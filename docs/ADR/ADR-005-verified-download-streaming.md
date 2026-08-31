# ADR-005: 検証済み大容量downloadのstreaming方式

- ステータス: **Accepted**
- 決定日: 2026-08-31
- 対象: Storage / API / Browser download

## 背景

authenticated API downloadは、DBのSHA-256とMinIO objectをHTTP 200前に照合するため、
全objectを一時fileへ取得していた。8MiBを超える部分はdiskへspoolされるため、500MiBの
並列downloadでbackend hostの一時領域を枯渇させる可能性がある。

Repositoryが固定するMinIO `RELEASE.2025-04-22T22-12-26Z` で、S3
`ChecksumSHA256`付きPUTと`ChecksumMode=ENABLED`付きGETが成功することを実測した。

## 判断

1. 新規uploadはDB・object metadataに加えて、S3 protocolの`ChecksumSHA256`を保存する。
2. download開始前に`ContentLength`、S3 `ChecksumSHA256`、DB SHA-256を照合する。
   一致するobjectは一時fileを作らずauthenticated APIから直接streamする。Boto3の
   response checksum validationを明示的に有効化し、applicationでも受信byteを再計算する。
   最終1MiBはlook-aheadで保留し、SDKとapplicationの検証成功後にだけclientへ渡す。
3. protocol checksumがないlegacy objectは、従来どおり全量SHA-256検証後にHTTP 200を返す。
   その一時領域はprocess start time付きreservation fileと`flock`で全worker間共有し、
   Composeではtmpfs hard capも設定する。
4. failure contractは次のとおりとする。

| 状態 | HTTP | 動作 |
|---|---:|---|
| per-request上限超過 | 413 | downloadを開始しない |
| 共有quota使用中 | 429 | `Retry-After: 30`を返す |
| filesystem容量不足 | 507 | downloadを開始しない |
| 開始前のsize/checksum不一致 | 502 | integrity failureとして拒否 |
| streaming中のchecksum/接続失敗 | 接続中断 | browser側の保存をabortし、完成fileとして確定しない |

5. browserはcapability detectionで分岐する。

| Browser capability | 方針 |
|---|---|
| `showSaveFilePicker`あり | `ReadableStream.pipeTo()`でdiskへ直接保存 |
| APIなし・100MiB以下 | Blob fallback |
| APIなし・100MiB超 | memory枯渇を避けるためUIで拒否 |

## 比較した方式

| 方式 | 判断 | 理由 |
|---|---|---|
| `aioboto3`へ全面移行 | 見送り | 新規dependencyとclient lifecycle管理が増える。現状はsync iteratorをStarlette threadpoolがchunk単位で実行し、全量取得中のthread専有を解消できる |
| nginx/download gatewayへ委譲 | 見送り | 組織membershipとDB checksumをgatewayへ安全に伝える内部署名・失効設計が必要で、現在の単一host MVPには過剰 |
| boto3 protocol checksum + legacy fallback | 採用 | 既存storage abstractionを維持し、新規objectの一時disk使用をゼロにできる |

## 結果と制約

- 新規objectの並列downloadはbackend一時disk quotaを消費しない。
- legacy objectは安全性を下げず、共有quotaでfail-closedになる。
- streaming開始後のfailureをJSON errorへ変換することはできない。File System Access API経路は
  destinationをabortし、Blob経路はfetch failureとして完成fileを生成しない。
- 既存objectを一括再uploadしない。完全backup/restore後に必要ならchecksum付与移行を別途行う。

参考: [Boto3 put_object](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/put_object.html),
[Boto3 get_object](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/get_object.html)
