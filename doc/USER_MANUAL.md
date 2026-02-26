# SCIdrawer 用户手册

本文档用于说明平台的功能模块与使用方法。

## 1. 快速开始
1) 启动服务  
```bash
python app.py
```
2) 浏览器访问  
`http://<你的公网IP>:<端口>`

## 2. 仪表盘
仪表盘展示 API 余额与模型状态。

- 积分余额：使用已设置的 API Key 查询当前余额。
- API Key：显示是否已经在“API 密钥”页面配置。
- API 主机：显示当前 API 主机（国内直连或海外节点）。
- 模型状态：按当前支持的模型列表批量查询状态，可点击“刷新”更新。

常见问题：
- 余额显示 `--`：请先设置 API Key。若仍失败，会弹出错误提示。

## 3. API 密钥管理
用于保存与管理你的 API Key。

1) 进入“API 密钥”页面  
2) 输入 API Key 并点击“添加并设为当前”  
3) 可测试、删除或切换当前 Key

## 4. 图像生成
支持文本提示词 + 参数控制，并可上传参考图。本平台集成了先进的 AI 绘图模型（如 Nano Banana 系列），特别适合用于生成高质量的科研插图。

### 4.1 基本生成流程
1) **输入提示词**：在文本框中详细描述你想要的图像内容。
2) **选择模型**：
   - `nano-banana-fast`：速度快，适合快速验证想法。
   - `nano-banana`：标准模型，平衡速度与质量。
   - `nano-banana-pro`：高质量模型，细节更丰富，适合最终出图。
3) **设置参数**：选择合适的画面比例（如 16:9, 4:3）和分辨率。
4) **点击“生成图像”**：等待 AI 处理完成。

### 4.2 科研绘图指南
Nano Banana 系列模型在科研绘图方面表现出色。为了获得最佳效果，请遵循以下指南。

#### 4.2.1 生成科研绘图的关键
**Prompt（提示词）要像写说明书一样，描述越详细，模型生成的图像越结构化，效果越好。**

一个实用的科研插图 Prompt，通常需要包含以下要素：

*   **主题**：你要画什么（机制 / 流程 / 对比）
*   **风格**：简洁、技术图、论文可用
*   **标注要求**：哪些元素必须出现、使用英文标签
*   **布局规则**：箭头、模块、层级关系
*   **限制条件**：避免艺术化、渐变、装饰效果

#### 4.2.2 实用 Prompt 案例库

以下是 7 个经过验证的科研绘图 Prompt 模板，您可以直接复制并根据需要修改：

**1️⃣ 信息图（案例：单细胞测序的优势）**
> "Produce an infographic summarizing the key advantages of single-cell RNA sequencing. Use subtle colors, icon-like shapes, and concise English text. Focus on clarity and avoid decorative backgrounds or artistic gradients."

**2️⃣ 概念图（案例：微生物组与免疫的关系）**
> "Create a conceptual diagram illustrating how microbiome composition influences host immunity. Use simple icons for microbes and immune cells, with arrows showing interactions. Maintain a clean, high-resolution style with clear English labels."

**3️⃣ 数据分析流程图（案例：RNA-seq分析管线）**
> "Create a bioinformatics pipeline diagram for RNA-seq analysis, including raw data QC, trimming, alignment, read counting, differential expression, and visualization. Use a horizontal layout with consistent color coding and clear English labels."

**4️⃣ 作用机制图（案例：抗体阻断机制）**
> "Visualize the mechanism of action of an antibody therapy blocking a receptor–ligand interaction. Show the cell membrane, receptors, antibodies, and downstream inhibition. Use clear labeling and avoid artistic effects or gradients."

**5️⃣ 多组学整合流程示意图**
> "Draw a schematic representing the integration of genomics, transcriptomics, proteomics, and metabolomics data into a unified analysis pipeline. Use four modules feeding into one central analytical framework. Ensure logical structure and clarity."

**6️⃣ 方法对比图（案例：电子显微镜 vs 共聚焦显微镜）**
> "Create a comparison diagram showing the differences between electron microscopy and confocal microscopy. Include imaging resolution, sample preparation, and typical applications. Use a balanced two-column layout with clear English labels and no decorative background."

**7️⃣ 实验设计图（案例：随机对照临床试验）**
> "Generate a study design diagram for a randomized controlled trial comparing Drug A vs placebo. Include participant enrollment, randomization, intervention, follow-up, and endpoint assessment. Keep the visual style neutral and suitable for journal submission."

#### 4.2.3 重要提示
> **⚠️ AI 永远不负责“画得正确”！**

虽然 Nano Banana 极大提升了科研绘图的效率，但它并不能替你判断科学内容是否正确。
Nano Banana 的出现，并不是为了让科研人员少思考，而是让大家少被重复劳动消耗。

**请记住，在实际使用中，一定不要忘了人工校对！**

### 4.3 参考图上传
支持上传参考图（最多 3 张，每张不超过 5MB）。
上传后会在列表中展示缩略图与文件信息，可点击删除。参考图可以帮助 AI 更好地理解你想要的构图或风格。

## 5. 智能对话
该模块目前显示为“正在开发中”，暂不可用。

## 6. 系统设置
可配置 API 主机与默认模型等选项。

- API 主机：国内直连 / 海外节点  
- 图像生成模型：选择默认绘图模型  
- 对话模型：选择默认对话模型（当前模块仍在开发中）

## 7. 常见问题
1) 余额无法获取  
   - 检查 API Key 是否正确  
   - 检查主机是否可达  

2) 模型状态为异常  
   - 查看返回错误信息，稍后重试  

