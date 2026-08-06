# Synervia 后端执行计划

> 状态：执行中
> 更新时间：2026-07-21
> 范围：`product/synervia/backend` 及其依赖的后端服务

## 当前进度

后端质量基线、embedding provider 和 Phase 0B 完整知识问答冒烟已经完成。当前进入
Phase 1A，目标是补齐异步入库在失败、重试和清理路径上的一致性。

已经验证的基线：

- `make backend-check` 通过；
- Ruff lint 和格式检查通过；
- 当前 `ty check` 命令成功退出，仍有 42 条 warning 级诊断作为技术债记录；
- 后端测试通过：384 passed，4 skipped；
- 根目录产品 CI 已配置在 `.github/workflows/product-ci.yml`。

Embedding 实现状态：

- [x] 通过 FastEmbed 提供本地 CPU embedding；
- [x] 默认中文模型为 `BAAI/bge-small-zh-v1.5`；
- [x] 已确认当前安装的 FastEmbed 版本支持默认模型；
- [x] 支持 `local`、`openai` 和 `openrouter` provider 路由；
- [x] 支持独立的 embedding API key 和 base URL 覆盖配置；
- [x] 已知模型自动推断维度，未知模型支持显式配置维度；
- [x] 本地模型分别使用查询和文档专用的 embedding 方法；
- [x] 已接入模型缓存和应用启动预热；
- [x] 已覆盖配置、provider 路由、缓存使用和维度处理的单元测试；
- [x] 在运行中的应用内验证真实模型下载和推理；
- [x] 验证真实向量写入 pgvector 并可以查询；
- [x] 验证从上传到回答的完整流程，并返回可追溯引用。

上述最后三项已通过 Phase 0B 真实冒烟确认完成。

## 执行顺序

```text
Phase 0B：完整后端链路冒烟测试 [完成]
  -> Phase 1A：入库与 Worker 正确性 [进行中]
  -> Phase 1B：组织与知识库隔离
  -> Phase 1C：检索、引用与无证据策略
  -> Phase 1D：端到端测试与 RAG 评测
```

在 Phase 1 的隔离和正确性检查通过之前，不扩展多 Agent 行为、不增加大量连接器，
也不开放未经审批的写操作。

## Phase 0B：完整后端链路冒烟测试（已完成）

### 目标

证明一个全新的本地环境可以使用默认本地 embedding 模型跑通知识问答全流程。

### 任务

- [x] 在 `product/synervia` 下执行 `make bootstrap` 启动后端栈；
- [x] 确认 PostgreSQL、pgvector、Redis、API 和 Celery Worker 健康；
- [x] 确认数据库迁移到达当前 head，管理员初始化可以幂等执行；
- [x] 启动前端，仅将其作为验证后端流程的客户端；
- [x] 登录并创建组织和知识库；
- [x] 上传一份小型、固定、包含唯一可识别事实的中文测试文档；
- [x] 确认 Worker 正确推进文档入库状态；
- [x] 确认 FastEmbed 下载并缓存 `BAAI/bge-small-zh-v1.5`；
- [x] 确认保存的向量维度为 512，且 pgvector 中存在对应 chunks；
- [x] 搜索测试事实，确认返回预期 chunk；
- [x] 在聊天中提出同一问题，确认回答包含能定位到源文档的引用；
- [x] 重启服务栈后重复核心流程，确认状态没有丢失或损坏；
- [x] 完成 Phase 0B 冒烟并由项目执行结果确认整条链路通过。

### 完成标准

- 新检出的仓库可以只按文档命令得到带引用的知识回答；
- 本地 embedding 推理不依赖 embedding API key；
- API、数据库记录、Celery 结果和 pgvector 数据对成功状态的描述一致；
- 重复执行 bootstrap 和重启服务不会破坏环境；
- 冒烟中发现的问题必须带回归测试修复，或有证据地归入 Phase 1A。

## Phase 1A：入库与 Worker 正确性（当前阶段）

### 目标

让异步入库状态真实、可重试、可恢复。

### 任务

- [ ] 定义并强制执行状态机：
  `queued -> processing -> retrying -> completed | failed`；
- [x] 防止入库结果失败但 Celery 任务被标记成功；
- [ ] 仅在重试耗尽后将文档标记为最终失败；
- [x] 保存 vector store 实际返回的 vector document ID；
- [x] 保存实际写入的 chunk 数量，不使用占位值；
- [ ] 保证入库幂等，重试不能创建重复 chunks；
- [ ] 在成功、最终失败和重试路径中正确清理临时上传文件；
- [x] 需要后续重试或下载时保留原始存储文档；
- [ ] 修正成功、部分失败、取消和重试情况下的同步统计；
- [ ] 增加结构化日志，至少包含 document ID、knowledge-base ID、task ID、
  当前尝试次数、状态转换、耗时和错误类别。

### 必需测试

- 入库成功及其状态转换；
- 写入向量前发生解析失败；
- embedding 失败和维度不匹配；
- embedding 完成后 vector store 写入失败；
- 可重试错误发生后下一次执行成功；
- 重试耗尽后进入最终失败；
- 重复投递任务及其幂等重放；
- 每条最终路径都正确清理临时文件；
- 准确保存 vector document ID 和 chunk 数量；
- 同一次同步中同时出现成功和失败文件。

### 完成标准

- SQL 状态、Celery 状态和 pgvector 内容描述相同的执行结果；
- 重试不会创建重复向量记录，也不会过早报告最终失败；
- 所有最终执行结果均不会遗留临时上传文件。

## Phase 1B：组织与知识库隔离

### 目标

将服务端解析并授权的 `knowledge_base_id` 设为访问 RAG 数据的唯一可信入口。

### 任务

- [ ] 根据已认证用户和组织解析其可访问知识库；
- [ ] 拒绝客户端、Agent 或 Worker 提供的、并非由已授权知识库派生的 collection
  名称；
- [ ] 知识库 API、RAG API、Agent 工具、CLI/任务入口和 Worker 执行统一使用同一
  授权服务；
- [ ] 在向量存储边界持久化 organization ID、knowledge-base ID、document ID 和稳定
  chunk 标识；
- [ ] 统一约束列表、上传、搜索、重试、删除和同步操作；
- [ ] 定义默认知识库和向量 collection 的安全生命周期；
- [ ] 删除或保护会绕过知识库授权的旧版全局 collection 接口。

### 必需测试

- 两个组织之间不能互相列表、上传、搜索、重试、同步或删除文档；
- API 和 Agent 工具都会拒绝伪造的 collection 名称或 knowledge-base ID；
- 已排队任务使用可信的持久化标识重新校验授权和资源归属；
- 个人、组织和应用级知识库继续遵循各自不同的访问策略。

### 完成标准

即使手工构造 API 请求、Agent 参数或任务 payload，也无法跨越组织或知识库边界。

## Phase 1C：检索、引用与无证据策略

### 目标

存在有效证据时返回有用结果；没有有效证据时，禁止生成虚构的企业事实。

### 任务

- [ ] 保留原始查询，并增加可审计的查询改写；
- [ ] 定义向量与关键词候选召回，以及混合结果合并策略；
- [ ] 让 reranking 可以配置，并在 Agent 检索路径中实际生效；
- [ ] 根据真实 cosine score 语义校准阈值；
- [ ] 低于阈值时返回无证据结果，禁止向 LLM 传入弱相关上下文；
- [ ] 返回结构化引用，包含 organization、knowledge base、document、稳定 document
  ID、chunk ID、page，以及存在时的源位置；
- [ ] 确保引用标识只能通过经过授权的后端接口解析。

### 完成标准

- 关键结论可以追溯到具体存储证据；
- 没有合格证据的问题返回明确的无证据回答；
- 检索与引用行为具有足够的可测量性和确定性，可以执行评测。

## Phase 1D：端到端测试与评测

### 任务

- [ ] 增加使用启用 pgvector 的 PostgreSQL 集成测试；
- [ ] 覆盖上传、Worker 入库、检索、回答生成和引用解析；
- [ ] 建立小型评测集，包含有答案、无答案、跨组织和边界查询；
- [ ] 记录 Recall@K、引用正确率、忠实度、无答案识别率和 P95 检索延迟；
- [ ] 将核心隔离测试和 RAG 冒烟测试接入产品 CI。

### 完成标准

- 跨组织检索被阻止；
- 失败状态准确；
- 引用可以解析到正确证据；
- 约定的最低评测阈值在 CI 或有文档记录的评测任务中通过。

## 质量技术债

以下问题不阻塞 Phase 0B，但修改相关模块时必须逐步减少：

- 将当前 42 条后端类型诊断转为可跟踪的消减清单，优先处理 RAG/Worker 正确性
  相关 warning；
- 使用真实 PostgreSQL 运行 migration 测试；当前标准本地测试中有 4 个 migration
  测试被跳过；
- 对 mock session 无法验证的 SQL、pgvector filter、事务行为和租户隔离增加真实
  数据库测试；
- 保持 `make backend-check` 为本地和 CI 的统一入口，并禁止 warning 数量继续增长。

## 下一次立即执行

继续 Phase 1A，只处理当前代码尚未覆盖的失败与重试路径：

```text
显式状态转换
  -> 重试期间保持 retrying
  -> 重试耗尽后才写 failed
  -> 重复投递不产生重复 chunks
  -> 成功或最终失败后清理临时文件
  -> 同步统计与实际入库结果一致
  -> 自动化测试覆盖全部终态
```

Phase 0B 不再重复执行为开发任务；后续只在 Phase 1A 修改需要回归验证时复用该冒烟
链路。完成上述剩余项并通过测试后，进入 Phase 1B。
