# AI论文检测工具开发文档

## 一、项目说明
AI论文检测工具用于识别文本中由AI生成的内容比例，提供直观、准确的检测报告，帮助用户评估论文原创性。

## 二、开发环境与技术栈

### 前端
- **框架**：React.js（推荐）
- **UI组件**：Ant Design / Tailwind CSS
- **可视化库**：Echarts / Chart.js

### 后端
- **编程语言**：Python 3.9+
- **Web框架**：FastAPI
- **AI模型与API**：OpenAI GPT API / Copyleaks AI Content Detection API（根据实际需求选择）
- **文档解析库**：PyMuPDF（PDF）、python-docx（DOCX）

### 数据库
- SQLite / PostgreSQL

### 部署环境
- Docker容器
- 云服务器（腾讯云/AWS）

## 三、项目结构

```
project-root/
├── frontend/
│   ├── src/
│   │   ├── components/   # 公共组件
│   │   ├── pages/        # 页面组件
│   │   ├── api/          # API调用接口
│   │   └── utils/        # 工具函数
│   └── public/
├── backend/
│   ├── app/
│   │   ├── routers/      # API路由
│   │   ├── schemas/      # 数据模型定义
│   │   ├── services/     # 核心业务逻辑
│   │   ├── utils/        # 工具与辅助函数
│   │   └── main.py       # FastAPI入口
│   └── requirements.txt  # 依赖管理
├── Dockerfile
└── docker-compose.yml
```

## 四、接口设计

### 1. 上传论文接口
- URL：`/api/upload`
- Method：`POST`
- Params：文件流（支持PDF、DOC、TXT）
- Response：`{"task_id": "string", "status": "uploaded"}`

### 2. 论文检测接口
- URL：`/api/detect/{task_id}`
- Method：`GET`
- Response：
```json
{
  "task_id": "string",
  "status": "completed",
  "ai_generated_percentage": 23.5,
  "details": [
    {"paragraph": "文本内容", "ai_generated": true, "reason": "低困惑度"},
    {"paragraph": "文本内容", "ai_generated": false, "reason": "语言多样性高"}
  ]
}
```

### 3. 报告导出接口
- URL：`/api/report/{task_id}`
- Method：`GET`
- Response：PDF文件流

## 五、开发流程
1. 前端搭建基础页面，包含上传组件、结果展示、可视化图表。
2. 后端搭建FastAPI，完成文件上传、解析、调用AI检测API。
3. 对接前后端接口，完善交互逻辑。
4. 部署到Docker环境，测试稳定性与性能。

## 六、注意事项
- 严格遵守隐私保护原则，文件解析后不保存用户原始文件。
- API调用限制、异常处理需完善，保证工具健壮性。
- 模型调用成本需提前评估，优化API调用次数。

---

此文档用于辅助开发实现，便于团队快速开展工作，明确任务分工与实现细节。

