# AI论文检测工具

一个用于检测论文中AI生成内容比例的工具，提供详细的分析报告。

## 功能特点

- 支持PDF、DOCX和TXT格式的文件上传
- 自动分析文本，标识AI生成内容的比例
- 提供段落级别的详细分析
- 生成可视化检测报告
- 支持PDF报告导出
- 完整的用户管理和历史记录功能

## 技术栈

### 前端
- React.js
- Ant Design
- Echarts

### 后端
- Python 3.9+
- FastAPI
- SQLite数据库

## 快速开始

### 使用Docker

使用Docker Compose启动整个应用：

```bash
docker-compose up --build
```

然后访问：
- 前端界面：http://localhost:3000
- 后端API：http://localhost:8000

### 手动安装

#### 后端

1. 安装依赖：
```bash
cd backend
pip install -r requirements.txt
```

2. 运行后端服务：
```bash
python run.py
```

#### 前端

1. 安装依赖：
```bash
cd frontend
npm install
```

2. 运行开发服务器：
```bash
npm start
```

## 接口文档

启动后端服务后，可访问 Swagger UI 接口文档：

http://localhost:8000/docs

## 配置说明

### 环境变量

- `DATABASE_URL`: 数据库连接URL
- `SECRET_KEY`: JWT密钥
- `AI_DETECTION_API_KEY`: AI检测API密钥
- `AI_DETECTION_API_ENDPOINT`: AI检测API端点

## 项目结构

```
project-root/
├── frontend/          # React前端
├── backend/           # FastAPI后端
├── uploads/           # 上传文件存储（挂载卷）
├── docker-compose.yml # Docker配置
└── README.md          # 项目说明
```

## 使用方法

1. 注册/登录账号
2. 上传论文文件（PDF、DOCX或TXT）
3. 开始AI内容检测
4. 查看检测结果和详细报告
5. 导出PDF报告（可选）

## 许可证

MIT 