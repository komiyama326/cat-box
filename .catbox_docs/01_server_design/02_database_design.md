# データベース設計 (初期)

## テーブル定義 (SQLAlchemyモデル)

### User
- `id`: Integer, Primary Key
- `email`: String, Unique
- `hashed_password`: String
- `username`: String, Unique
- `plan`: Enum('basic', 'premium'), default 'basic'
- `points`: Integer, default 0

### App
- `id`: Integer, Primary Key
- `name`: String
- `description`: Text
- `version`: String
- `download_url`: String
- `icon_url`: String
- `owner_id`: ForeignKey('users.id')
- `app_type`: Enum('basic', 'premium'), default 'basic'
- `status`: Enum('public', 'private', 'reported'), default 'public'