# 規則類検索システム（バックエンド仕様）

本リポジトリは、規則類（規程・規則等）を **GitHub Pages 上で公開し、全文検索を可能にするためのバックエンド処理**を提供する。

本システムは **静的サイト構成**を採用し、バックエンドサーバを持たない。
規則データは GitHub Repository に保存され、GitHub Actions により検索インデックスおよび一覧ファイルが生成される。

---

## 1. システム概要

本システムは以下の要素で構成される。

* 規則XMLファイル
* 規則メタデータJSON
* 検索インデックス生成スクリプト
* GitHub Actions
* GitHub Pages

システム構成は次の通りである。

```
Frontend
   │
   │ GitHub REST API
   ▼
Repository
   ├ rules XML
   ├ metadata JSON
   │
   ▼
GitHub Actions
   ├ 現行改正判定
   ├ XML解析
   ├ 検索index生成
   └ 一覧ファイル生成
   │
   ▼
GitHub Pages
   ├ rules
   ├ metadata
   ├ rules-index.json
   └ search-index.json
```

---

## 2. 想定規模

| 項目      | 上限     |
| ------- | ------ |
| 規則数     | 約100   |
| 条文数     | 約5000  |
| 検索index | 約2〜3MB |

この規模であれば、静的検索（ブラウザ検索）で十分対応可能である。

---

## 3. ディレクトリ構造

```
repository/

├ rules/
│   ├ {rule_id}/
│   │   ├ {revision_id}.xml
│   │   └ ...
│   └ ...
│
├ metadata/
│   ├ {rule_id}.json
│   └ ...
│
├ public/
│   ├ rules/
│   ├ metadata/
│   ├ rules-index.json
│   └ search/
│       ├ documents.json
│       └ search-index.json
│
├ scripts/
│   ├ build_index.py
│   ├ parse_xml.py
│   ├ resolve_current_revision.py
│   └ tokenizer.py
│
├ requirements.txt
│
└ .github/
    └ workflows/
        └ build.yml
```

---

## 4. 規則識別

規則は **rule_id** により一意に識別される。

```
rules/{rule_id}/
```

rule_idは8桁の文字列であり、以下の要素で構成される。

- 制定年（4桁）
    + 2025年制定なら`2025`
- 種別コード（3桁）
    + 規約: `CON`
    + 規程: `LAW`
    + 規則: `RUL`
- 制定主体コード（3桁）
    + 1桁目: 自治機関の種類
        * 予算委員会: `1`
        * 選挙管理委員会 `2`
        * サークル連合 `3`
        * 文化祭実行委員会 `4`
        * 運動会実行委員会 `5`
    + 2,3桁目: 自治機関内の組織
        * `01`
            - 本会議（サークル連合以外）
            - サークル連合総会
        * `02`
            - 議長団（選挙管理委員会、サークル連合以外）
            - サークル連合議長
            - 選挙管理委員会議事運営局
        * `03`
            - 予算委員会参議会
        * `04`
            - 予算委員会事務局
            - 選挙管理委員会執務局
            - サークル連合事務局
        * `05`
            - 予算委員会法制局
        * `06`
            - 予算委員会監査局
            - サークル連合監査委員会
        * `07`
            - 選挙管理委員会選挙運営局
        * `08`
            - サークル連合会計局
        * `09`
            - 文化祭実行委員会実務調整会議
    + 例外
        * 複数機関を跨いで制定されたもの（ガイドラインなど）
            - 1桁目: 協定を意味する`6`
            - 2,3桁目: 協定を結んだ2つの機関を数字が小さい順に並べる
                + 例: 予算委員会と文化祭実行委員会のガイドラインなら、`14` 
        * 上記で表現できない場合
            - `999`
            - その場合は、idの設計を見直し、バージョンを上げるのが良いだろう
   
- 規則類の連番（3桁）
- バージョン（1桁）
    + 現在は`1`

※rule_idは、運用中変更されない。

---

## 5. 改正管理

規則の各改正段階は **revision_id（改正ID）** により識別される。

revision_id は以下の要素をアンダーバーで繋いだ識別子である。

* 規則ID
* 施行日
    + 本リポジトリ運用開始日よりも前に施行されていた等の理由で、不明な場合は0を埋める
    + 施行日が未確定の場合は、Xを埋める。確定し次第修正する。
* 当該改正を行った規則ID
    + 当該版が初版の場合は、0を埋める。
    + 改正規程が不明な場合は、Xを埋める。

改正XMLの保存場所

```
rules/{rule_id}/{revision_id}.xml
```

### 改正IDの変更について

revision_id は施行日等の変更に伴い **変更される場合がある**。

そのため revision_id は **永続識別子ではなく、改正段階を識別する運用上のID**として扱う。

---

## 6. metadata JSON

規則の基本情報および改正履歴は metadata JSON に保存する。

```
metadata/{rule_id}.json
```

---

## 7. 現行改正の決定

検索インデックス生成時に、metadata の施行日から **現行改正**を決定する。

アルゴリズム

```
1. effective_date <= 今日
2. 上記条件を満たす改正のうち、effective_date が最大のもの
```

この改正段階のXMLを **全文検索の対象**とする。

---

## 8. 規則XML仕様

規則XMLは **e-LAWS 法令標準XMLスキーマ**を採用する。

条番号は `Article` 要素の `Num` 属性により取得する。

XML構造の詳細は **e-LAWS法令標準XML仕様**に従う。

---

## 9. 検索対象

全文検索対象は

**現行改正のみ**

とする。

ただし、XMLはすべて保存されるため **過去改正の閲覧は可能**である。

---

## 10. documents.json

検索対象条文データ。

```
public/search/documents.json
```

doc_id

```
{rule_id}-{article_num}
```

---

## 11. 検索インデックス

検索インデックスは

```
public/search/search-index.json
```

として生成する。

検索エンジンは **FlexSearch** を想定する。

---

## 12. rules-index.json

規則一覧を取得するためのファイル。

```
public/rules-index.json
```

フロントエンドはこのファイルのみ取得すれば、規則一覧を表示できる。

---

## 13. GitHub Actions

規則データ更新時に以下を実行する。

1. metadata読み込み
2. 現行改正決定
3. XML解析
4. 条文抽出
5. 形態素解析
6. documents.json生成
7. search-index.json生成
8. rules-index.json生成
9. GitHub Pages更新

トリガー

```
push:
  rules/**
  metadata/**
```

---

## 14. tokenizer

日本語検索のため **SudachiPy** を利用する。

requirements

```
sudachipy
sudachidict_core
```

---

## 15. GitHub Pages公開

公開されるファイル

```
/rules/{rule_id}/{revision_id}.xml
/metadata/{rule_id}.json
/rules-index.json
/search/documents.json
/search/search-index.json
```

---

## 16. フロントエンドからの更新

フロントエンドは GitHub REST API を用いて以下を push する。

```
rules/{rule_id}/{revision_id}.xml
metadata/{rule_id}.json
```

push後、自動的に GitHub Actions が実行され検索indexが更新される。

---

## 17. 設計方針

本システムは以下の設計原則に基づく。

* バックエンドサーバを持たない
* GitHub Pages による静的配信
* XMLを原本として保存
* metadataで改正管理
* CIで検索index生成
* 現行規定のみ全文検索

これにより、低運用コストで規則検索システムを構築できる。

---
