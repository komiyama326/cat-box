# API設計

## 基本原則
- RESTful API
- URLパス: `/api/v1/...`
- レスポンス形式: JSON
- 認証: JWTをAuthorizationヘッダーに Bearer トークンとして付与

## エラーレスポンス形式
エラー発生時は、以下のJSON形式で統一する。
```json
{
  "detail": "具体的なエラーメッセージ"
}