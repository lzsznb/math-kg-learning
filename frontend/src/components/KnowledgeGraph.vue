<template>
  <div class="knowledge-graph">
    <!-- 用户栏 -->
    <div class="user-bar">
      <div class="user-info" v-if="currentUser">
        <span class="user-name">👤 {{ currentUser }}</span>
        <button class="btn btn-sm" @click="handleLogout">退出登录</button>
        <button class="btn btn-sm btn-danger" @click="showDeregisterConfirm = true">注销账号</button>
      </div>
      <div class="user-info" v-else>
        <button class="btn btn-sm" @click="showLoginDialog = true; isRegister = false">登录</button>
        <button class="btn btn-sm" @click="showLoginDialog = true; isRegister = true">注册</button>
      </div>
    </div>

    <div class="graph-header">
      <h2>知识图谱</h2>
      <div class="controls">
        <button class="btn" @click="toggleFullscreen">
          {{ isFullscreen ? '退出全屏' : '全屏模式' }}
        </button>
        <button class="btn" @click="resetLayout">重置布局</button>
        <button class="btn" @click="toggleLabels">{{ showLabels ? '隐藏标签' : '显示标签' }}</button>
        <button class="btn" @click="toggleAlgorithmPanel">
          {{ showAlgorithms ? '隐藏算法' : '网络算法' }}
        </button>
        <button class="btn btn-diagnosis" @click="runDiagnosis" :disabled="!currentUser">
          🔍智能诊断
        </button>
        <button class="btn btn-suggestion" @click="showDailySuggestions = !showDailySuggestions" v-if="dailySuggestions.length > 0">
          💡每日建议 ({{ dailySuggestions.length }})
        </button>
        <button class="btn btn-dashboard" @click="toggleDashboard">
          📊数据仪表盘
        </button>
        <button class="btn btn-chat" @click="toggleChat">
          🤖 AI 问答
        </button>
        <button class="btn" @click="showNetworkAnalysis = !showNetworkAnalysis; if (showNetworkAnalysis) loadNetworkAnalysis()">
          📈网络科学分析
        </button>
        <button class="btn btn-triples" @click="loadTriples">
          🔗三元组浏览
        </button>
        <button class="btn btn-reasoning" @click="showReasoning = !showReasoning; if (showReasoning && selectedNode) loadReasoning()">
          🧠语义推理
        </button>
        <button class="btn btn-search" @click="showKGSearch = !showKGSearch; if (showKGSearch) loadKGSearch()">
          🔍 语义检索
        </button>
        <button class="btn btn-extract" @click="showExtraction = !showExtraction; if (showExtraction) loadExtraction()">
          🏗️ 实体抽取
        </button>
        <button class="btn btn-hybrid" @click="showHybrid = !showHybrid; if (showHybrid) loadHybrid()">
          🎯混合推荐
        </button>
        <button class="btn" @click="showGraph = !showGraph">
          {{ showGraph ? '隐藏图谱' : '显示图谱' }}
        </button>
      </div>
    </div>

    <div class="legend" v-if="modules.length > 0">
      <span v-for="mod in modules" :key="mod" class="legend-item">
        <span class="legend-dot" :style="{ background: getModuleColor(mod) }"></span>
        {{ mod }}
      </span>
      <span class="legend-item"><span class="legend-dot" style="background: #52c41a"></span>已会</span>
      <span class="legend-item"><span class="legend-dot" style="background: #f5222d"></span>薄弱</span>
      <span class="legend-item"><span class="legend-dot" style="background: #ccc"></span>未学</span>
    </div>

    <div class="graph-body" v-show="showGraph">
      <div ref="chartRef" class="chart-container" v-show="!loading"></div>

      <div v-if="selectedNode" class="detail-panel">
        <div class="detail-header">
          <h3>{{ selectedNode.name }} <span style="font-size:0.75rem;color:#999;font-weight:normal">(ID: {{ selectedNode.id }})</span></h3>
          <button class="close-btn" @click="selectedNode = null">×</button>
        </div>
        <div class="detail-content">
          <div class="detail-row">
            <span class="label">所属模块</span>
            <span class="value" :style="{ color: getModuleColor(selectedNode.module) }">{{ selectedNode.module }}</span>
          </div>
          <div class="detail-row">
            <span class="label">难度等级</span>
            <span class="value">{{ '★'.repeat(selectedNode.difficulty) }}{{ '☆'.repeat(5 - selectedNode.difficulty) }}</span>
          </div>
          <div class="detail-row">
            <span class="label">学习状态</span>
            <span class="status-badge" :class="getStatusClass(getNodeStatus(selectedNode.id))">
              {{ getStatusText(getNodeStatus(selectedNode.id)) }}
            </span>
          </div>

          <!-- 状态切换按钮 -->
          <div class="status-actions">
            <button class="btn btn-sm" :class="{ active: getNodeStatus(selectedNode.id) === 'mastered' }"
              @click="setNodeStatus(selectedNode, 'mastered')" :disabled="!currentUser">
              已会
            </button>
            <button class="btn btn-sm" :class="{ active: getNodeStatus(selectedNode.id) === 'weak' }"
              @click="setNodeStatus(selectedNode, 'weak')" :disabled="!currentUser">
              薄弱
            </button>
            <button class="btn btn-sm" :class="{ active: getNodeStatus(selectedNode.id) === 'unlearned' }"
              @click="setNodeStatus(selectedNode, 'unlearned')" :disabled="!currentUser">
              未学
            </button>
          </div>

          <!-- 反事实推理 -->
          <div class="counterfactual-section">
            <button class="btn btn-sm btn-cf" @click="runCounterfactual" :disabled="counterfactualLoading">
              {{ counterfactualLoading ? '推理中...' : '🔮 假设掌握' }}
            </button>
            <select v-model="counterfactualSimStatus" class="cf-select">
              <option value="mastered">已会</option>
              <option value="weak">薄弱</option>
            </select>
          </div>

          <!-- 前置知识缺失检测 -->
          <div v-if="nodeDetail && missingPrerequisites.length > 0" class="warning-box">
            <p>⚠️ 请先掌握以下前置知识：</p>
            <div class="tag-list">
              <span v-for="pid in missingPrerequisites" :key="pid" class="tag tag-prereq" @click="focusNode(pid)">
                {{ getNodeName(pid) }}
              </span>
            </div>
          </div>

          <div class="detail-section" v-if="nodeDetail">
            <div class="detail-subsection">
              <h4>前置知识 ({{ nodeDetail.prerequisites.length }})</h4>
              <div class="tag-list">
                <span v-for="pid in nodeDetail.prerequisites" :key="pid"
                  class="tag" :class="getNodeStatus(pid) === 'mastered' ? 'tag-prereq' : 'tag-weak'"
                  @click="focusNode(pid)">
                  {{ getNodeName(pid) }}
                  <span class="status-mini">{{ getStatusText(getNodeStatus(pid)) }}</span>
                </span>
                <span v-if="nodeDetail.prerequisites.length === 0" class="empty-text">无前置依赖</span>
              </div>
            </div>
            <div class="detail-subsection">
              <h4>后置知识 ({{ nodeDetail.dependents.length }})</h4>
              <div class="tag-list">
                <span v-for="did in nodeDetail.dependents" :key="did"
                  class="tag tag-dependent" @click="focusNode(did)">
                  {{ getNodeName(did) }}
                </span>
                <span v-if="nodeDetail.dependents.length === 0" class="empty-text">无后置依赖</span>
              </div>
            </div>
          </div>

          <!-- 社区归属解释 -->
          <div class="detail-subsection" v-if="selectedNode">
            <button class="btn btn-sm" @click="loadCommunityExplain(selectedNode.id)" :disabled="communityExplainLoading" style="margin-top:0.2rem;">
              {{ communityExplainLoading ? '加载中...' : '🔍 解释社区归属' }}
            </button>
            <div v-if="communityExplain" class="community-explain" style="margin-top:0.4rem;padding:0.5rem;background:#f9f9f9;border-radius:6px;font-size:0.8rem;">
              <p><strong>所属社区：</strong>共 {{ communityExplain.community_size }} 个节点</p>
              <p><strong>主要模块：</strong>{{ communityExplain.main_module }}（{{ communityExplain.module_distribution?.[communityExplain.main_module] || 0 }} 个节点）</p>
              <p><strong>内部边数：</strong>{{ communityExplain.internal_edges }}，<strong>外部边数：</strong>{{ communityExplain.external_edges }}</p>
              <p><strong>社区密度：</strong>{{ (communityExplain.density * 100).toFixed(1) }}%</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 反事实推理结果 -->
      <div v-if="showCounterfactual && counterfactualResult" ref="cfPanelRef" class="algorithm-panel counterfactual-panel" :style="cfPanelPos.x !== null ? { left: cfPanelPos.x + 'px', top: cfPanelPos.y + 'px', right: 'auto' } : {}">
        <div class="panel-header" @mousedown="startCfDrag">>
          <h3>🔮 反事实推理：{{ selectedNode?.name }}</h3>
          <button class="close-btn" @click="showCounterfactual = false">×</button>
        </div>
        <div class="panel-body">
          <p class="cf-summary">{{ counterfactualResult.summary }}</p>

          <div class="cf-metrics">
            <div class="cf-metric-card">
              <div class="cf-metric-label">掌握度</div>
              <div class="cf-metric-compare">
                <span class="cf-before">{{ counterfactualResult.before.mastery_pct }}%</span>
                <span class="cf-arrow">→</span>
                <span class="cf-after">{{ counterfactualResult.after.mastery_pct }}%</span>
              </div>
              <div class="cf-delta positive">+{{ counterfactualResult.delta.mastery_pct_delta }}%</div>
            </div>
            <div class="cf-metric-card">
              <div class="cf-metric-label">已掌握</div>
              <div class="cf-metric-compare">
                <span class="cf-before">{{ counterfactualResult.before.mastered }}</span>
                <span class="cf-arrow">→</span>
                <span class="cf-after">{{ counterfactualResult.after.mastered }}</span>
              </div>
              <div class="cf-delta positive">+{{ counterfactualResult.delta.mastered_delta }}</div>
            </div>
            <div class="cf-metric-card">
              <div class="cf-metric-label">新增解锁知识点</div>
              <div class="cf-delta" :class="counterfactualResult.delta.unlocked_delta > 0 ? 'positive' : 'zero'">
                {{ counterfactualResult.delta.unlocked_delta > 0 ? '+' : '' }}{{ counterfactualResult.delta.unlocked_delta }}
              </div>
              <div class="cf-metric-sub">解锁后共有 {{ counterfactualResult.after.unlocked }} 个</div>
            </div>
          </div>

          <!-- 学习路径变化 -->
          <div class="cf-section" v-if="counterfactualResult.path_before && counterfactualResult.path_before.length">
            <h4>📌 学习路径变化</h4>
            <div class="cf-path-compare">
              <div class="cf-path-col">
                <div class="cf-path-label">当前</div>
                <div class="cf-path-nodes">
                  <span v-for="(n, i) in counterfactualResult.path_before" :key="n.id"
                    class="path-node" :class="{ current: n.id === selectedNode?.id }">
                    {{ n.name }}<span v-if="i < counterfactualResult.path_before.length - 1" class="path-connector"> → </span>
                  </span>
                </div>
                <div class="cf-path-length">{{ counterfactualResult.path_before.length }} 步</div>
              </div>
              <div class="cf-path-col">
                <div class="cf-path-label">假设后</div>
                <div class="cf-path-nodes">
                  <span v-for="(n, i) in counterfactualResult.path_after" :key="n.id"
                    class="path-node" :class="{ current: n.id === selectedNode?.id }">
                    {{ n.name }}<span v-if="i < counterfactualResult.path_after.length - 1" class="path-connector"> → </span>
                  </span>
                </div>
                <div class="cf-path-length">{{ counterfactualResult.path_after.length }} 步</div>
              </div>
            </div>
          </div>

          <!-- 模块影响 -->
          <div class="cf-section" v-if="counterfactualResult.module_delta && counterfactualResult.module_delta.length">
            <h4>📊 模块影响</h4>
            <div class="cf-module-list">
              <div v-for="m in counterfactualResult.module_delta.filter(m => m.delta > 0)" :key="m.module" class="cf-module-row">
                <span class="cf-module-name">{{ m.module }}</span>
                <div class="cf-module-bar-wrapper">
                  <div class="cf-module-bar-bg">
                    <div class="cf-module-bar-before" :style="{ width: m.before_pct + '%' }"></div>
                  </div>
                  <span class="cf-module-pct">{{ m.before_pct }}% → {{ m.after_pct }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 路径长度变化 -->
          <div class="cf-section" v-if="counterfactualResult.delta.path_length_delta !== null">
            <h4>⏱ 最短路径变化</h4>
            <p>从 <strong>{{ counterfactualResult.path_before?.length || '?' }} 步</strong>
               到 <strong>{{ counterfactualResult.path_after?.length || '?' }} 步</strong>
               <span v-if="counterfactualResult.delta.path_length_delta < 0">（缩短了 {{ -counterfactualResult.delta.path_length_delta }} 步 🎉）</span>
               <span v-else-if="counterfactualResult.delta.path_length_delta === 0">（无变化）</span>
               <span v-else>（增加了 {{ counterfactualResult.delta.path_length_delta }} 步）</span>
            </p>
          </div>
        </div>
      </div>

      <!-- 三元组浏览面板 -->
      <div v-if="showTriples" ref="triplesPanelRef" class="algorithm-panel triples-panel" :style="triplesPanelPos.x !== null ? { left: triplesPanelPos.x + 'px', top: triplesPanelPos.y + 'px', right: 'auto' } : {}">
        <div class="panel-header" @mousedown="startTriplesDrag">
          <h3>🔗 知识图谱三元组</h3>
          <button class="close-btn" @click="showTriples = false">×</button>
        </div>
        <div class="panel-body">
          <div class="triples-filter">
            <label>关系类型：</label>
            <select v-model="triplesRelationFilter" @change="loadTriples" class="cf-select">
              <option value="全部">全部 ({{ allTriplesCount }})</option>
              <option value="前置依赖">前置依赖</option>
              <option value="所属模块">所属模块</option>
              <option value="难度等级">难度等级</option>
            </select>
            <span class="triples-count" v-if="triplesData.length">共 {{ triplesData.length }} 条</span>
          </div>
          <div v-if="triplesLoading" class="loading-hint">加载中...</div>
          <div v-else class="triples-table-wrapper">
            <table class="triples-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>主体 (Subject)</th>
                  <th>关系 (Predicate)</th>
                  <th>客体 (Object)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(t, i) in triplesData" :key="i">
                  <td>{{ i + 1 }}</td>
                  <td>
                    <span class="triple-entity" :class="{ 'is-node': typeof t.subject_id === 'number' }"
                      @click="typeof t.subject_id === 'number' && focusNode(t.subject_id)">
                      {{ t.subject_name }}
                    </span>
                  </td>
                  <td><span class="triple-rel">{{ t.predicate }}</span></td>
                  <td>
                    <span class="triple-entity" :class="{ 'is-node': typeof t.object_id === 'number' }"
                      @click="typeof t.object_id === 'number' && focusNode(t.object_id)">
                      {{ t.object_name }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 语义推理面板 -->
      <div v-if="showReasoning" ref="reasoningPanelRef" class="algorithm-panel reasoning-panel" :style="reasoningPanelPos.x !== null ? { left: reasoningPanelPos.x + 'px', top: reasoningPanelPos.y + 'px', right: 'auto' } : {}">
        <div class="panel-header" @mousedown="startReasoningDrag">
          <h3>🧠 语义推理</h3>
          <button class="close-btn" @click="showReasoning = false">×</button>
        </div>
        <div class="panel-body">
          <div class="reasoning-controls">
            <label>推理规则：</label>
            <select v-model="reasoningRule" @change="reasoningResult = null" class="cf-select">
              <option value="transitive_prerequisite">前置传递推理</option>
              <option value="mastery_impact">掌握递推推理</option>
              <option value="all_paths">全路径推理</option>
              <option value="transitive_closure">传递闭包总览</option>
            </select>
          </div>

          <!-- 参数输入 -->
          <div class="reasoning-params" v-if="reasoningRule === 'all_paths'">
            <div class="reasoning-param-row">
              <label>起点实体ID：</label>
              <input v-model="reasoningSourceId" class="input-field" placeholder="输入知识点ID" type="number" />
            </div>
            <div class="reasoning-param-row">
              <label>终点实体ID：</label>
              <input v-model="reasoningTargetId" class="input-field" placeholder="输入知识点ID" type="number" />
            </div>
          </div>
          <div class="reasoning-params" v-else-if="reasoningRule === 'transitive_prerequisite' || reasoningRule === 'mastery_impact' || reasoningRule === 'transitive_closure'">
            <p class="reasoning-hint" v-if="selectedNode">
              ✅ 当前选中：<strong @click="focusNode(selectedNode.id)" style="cursor:pointer;color:#1677ff;">{{ selectedNode.name }}</strong>（ID: {{ selectedNode.id }}）
            </p>
            <p class="reasoning-hint" v-else>
              ⚠️ 请先在图谱中点击一个知识点节点，或输入 ID：
              <input v-model="reasoningSourceId" class="input-field" style="width:80px;display:inline-block;margin-left:0.3rem;" placeholder="ID" type="number" />
            </p>
          </div>

          <button class="btn btn-sm" @click="loadReasoning" :disabled="reasoningLoading" style="margin-top:0.5rem;">
            {{ reasoningLoading ? '推理中...' : '执行推理' }}
          </button>

          <!-- 推理结果 -->
          <div v-if="reasoningResult && !reasoningResult.error" class="reasoning-result">
            <div class="reasoning-explanation">
              <h4>📖 推理解释</h4>
              <p>{{ reasoningResult.explanation || reasoningResult.summary }}</p>
            </div>

            <div v-if="reasoningResult.rule" class="reasoning-rule-name">
              <span class="tag tag-reasoning">{{ reasoningResult.rule }}</span>
            </div>

            <!-- 前置传递：直接/间接前置 -->
            <div v-if="reasoningResult.direct_prerequisites !== undefined" class="reasoning-detail">
              <h4>📋 直接前置（{{ reasoningResult.direct_count }}）</h4>
              <div class="tag-list">
                <span v-for="p in reasoningResult.direct_prerequisites" :key="p.id" class="tag tag-prereq" @click="focusNode(p.id)">{{ p.name }}</span>
                <span v-if="reasoningResult.direct_count === 0" class="empty-text">无直接前置</span>
              </div>
              <h4 style="margin-top:0.5rem;">📋 间接前置（{{ reasoningResult.indirect_count }}）</h4>
              <div class="tag-list">
                <span v-for="p in reasoningResult.indirect_prerequisites" :key="p.id" class="tag tag-weak" @click="focusNode(p.id)">{{ p.name }}</span>
                <span v-if="reasoningResult.indirect_count === 0" class="empty-text">无间接前置</span>
              </div>
            </div>

            <!-- 掌握递推：影响列表 -->
            <div v-if="reasoningResult.impact" class="reasoning-detail">
              <h4>📋 影响的后置知识点（{{ reasoningResult.total_impacted }}）</h4>
              <div class="impact-list">
                <div v-for="x in reasoningResult.impact" :key="x.node_id" class="impact-item" :class="{ 'impact-ready': x.remaining_after_mastery === 0 }">
                  <span class="impact-name" @click="focusNode(x.node_id)">{{ x.node_name }}</span>
                  <span class="impact-info">剩余前置：{{ x.remaining_after_mastery }}</span>
                  <span v-if="x.remaining_after_mastery === 0" class="impact-badge">✅ 可学</span>
                </div>
              </div>
            </div>

            <!-- 全路径 -->
            <div v-if="reasoningResult.paths" class="reasoning-detail">
              <h4>📋 语义路径（共 {{ reasoningResult.total_paths }} 条，显示前 {{ reasoningResult.paths.length }} 条）</h4>
              <div v-for="p in reasoningResult.paths" :key="p.rank" class="path-item">
                <span class="path-rank">#{{ p.rank }}</span>
                <span class="path-nodes">
                  <span v-for="(n, i) in p.path" :key="n.id">
                    <span class="path-node-name" :class="{ 'path-current': n.id === (reasoningResult.target?.id || reasoningResult.node?.id) }" @click="focusNode(n.id)">{{ n.name }}</span>
                    <span v-if="i < p.path.length - 1" class="path-connector"> → </span>
                  </span>
                </span>
                <span class="path-len">{{ p.length }} 步</span>
              </div>
            </div>

            <!-- 传递闭包总览 -->
            <div v-if="reasoningResult.ancestors !== undefined && reasoningResult.direct_prerequisites === undefined" class="reasoning-detail">
              <h4>📋 间接前置（{{ reasoningResult.ancestor_count }}）</h4>
              <div class="tag-list">
                <span v-for="a in reasoningResult.ancestors.slice(0, 20)" :key="a.id" class="tag tag-prereq" @click="focusNode(a.id)">{{ a.name }}</span>
                <span v-if="reasoningResult.ancestor_count > 20" class="empty-text">……等共 {{ reasoningResult.ancestor_count }} 个</span>
              </div>
              <h4 style="margin-top:0.5rem;">📋 间接后置（{{ reasoningResult.descendant_count }}）</h4>
              <div class="tag-list">
                <span v-for="d in reasoningResult.descendants.slice(0, 20)" :key="d.id" class="tag tag-dependent" @click="focusNode(d.id)">{{ d.name }}</span>
                <span v-if="reasoningResult.descendant_count > 20" class="empty-text">……等共 {{ reasoningResult.descendant_count }} 个</span>
              </div>
              <!-- 推理链 -->
              <div v-if="reasoningResult.reasoning_paths" class="reasoning-paths-section">
                <h4 style="margin-top:0.5rem;">🔗 推理链样例</h4>
                <div v-for="(rp, i) in reasoningResult.reasoning_paths" :key="i" class="chain-item">
                  <div class="chain-type">{{ rp.type }}</div>
                  <div class="chain-nodes">
                    <span v-for="(n, j) in rp.path" :key="n.id">
                      <span class="path-node-name" @click="focusNode(n.id)">{{ n.name }}</span>
                      <span v-if="j < rp.path.length - 1" class="path-connector"> → </span>
                    </span>
                  </div>
                  <div class="chain-explain">{{ rp.explanation }}</div>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="reasoningResult && reasoningResult.error" class="error-text">{{ reasoningResult.error }}</div>
        </div>
      </div>

      <!-- 语义检索面板 -->
      <div v-if="showKGSearch" ref="searchPanelRef" class="algorithm-panel search-panel" :style="searchPanelPos.x !== null ? { left: searchPanelPos.x + 'px', top: searchPanelPos.y + 'px', right: 'auto' } : {}">
        <div class="panel-header" @mousedown="startSearchDrag">
          <h3>🔍 语义检索</h3>
          <button class="close-btn" @click="showKGSearch = false">×</button>
        </div>
        <div class="panel-body">
          <div class="search-filters">
            <div class="search-row">
              <label>知识点名称：</label>
              <input v-model="searchQuery.name" class="input-field" placeholder="模糊搜索" @keyup.enter="loadKGSearch" />
            </div>
            <div class="search-row">
              <label>所属模块：</label>
              <select v-model="searchQuery.module" class="cf-select" @change="loadKGSearch">
                <option value="">全部模块</option>
                <option v-for="m in modules" :key="m" :value="m">{{ m }}</option>
              </select>
            </div>
            <div class="search-row">
              <label>难度范围：</label>
              <select v-model="searchQuery.difficulty_min" class="cf-select" @change="loadKGSearch" style="width:70px;">
                <option :value="null">最低</option>
                <option :value="1">1</option>
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="4">4</option>
                <option :value="5">5</option>
              </select>
              <span style="margin:0 0.3rem;">—</span>
              <select v-model="searchQuery.difficulty_max" class="cf-select" @change="loadKGSearch" style="width:70px;">
                <option :value="null">最高</option>
                <option :value="1">1</option>
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="4">4</option>
                <option :value="5">5</option>
              </select>
            </div>
            <button class="btn btn-sm" @click="loadKGSearch" :disabled="searchLoading" style="margin-top:0.3rem;">
              {{ searchLoading ? '搜索中...' : '搜索' }}
            </button>
          </div>

          <div v-if="searchResults.length" class="search-results">
            <p class="search-count">共找到 {{ searchTotal }} 个匹配实体</p>
            <div class="search-result-list">
              <div v-for="r in searchResults" :key="r.id" class="search-result-item" @click="focusSearchNode(r.id)">
                <span class="search-result-name">{{ r.name }}</span>
                <span class="search-result-module" :style="{ color: getModuleColor(r.module), background: getModuleColor(r.module) + '22' }">{{ r.module }}</span>
                <span class="search-result-diff">{{ '★'.repeat(r.difficulty) }}{{ '☆'.repeat(5 - r.difficulty) }}</span>
              </div>
            </div>
          </div>
          <div v-else-if="!searchLoading" class="empty-text" style="text-align:center;padding:2rem;">
            {{ searchQuery.name || searchQuery.module || searchQuery.difficulty_min ? '无匹配结果' : '请输入搜索条件' }}
          </div>
        </div>
      </div>

      <!-- 实体抽取面板 -->
      <div v-if="showExtraction && extractionResult" ref="extractionPanelRef" class="algorithm-panel extraction-panel" :style="extractionPanelPos.x !== null ? { left: extractionPanelPos.x + 'px', top: extractionPanelPos.y + 'px', right: 'auto' } : {}">
        <div class="panel-header" @mousedown="startExtractionDrag">
          <h3>🏗️ 实体抽取管道</h3>
          <button class="close-btn" @click="showExtraction = false">×</button>
        </div>
        <div class="panel-body">
          <div v-if="extractionLoading" class="loading-hint">抽取中...</div>
          <div v-else>
            <div class="extraction-summary">
              <h4>📊 整体摘要</h4>
              <p class="cf-summary">{{ extractionResult.pipeline_summary }}</p>
            </div>

            <div class="extraction-metrics">
              <div class="cf-metric-card"><div class="cf-metric-label">实体数</div><div class="cf-after">{{ extractionResult.entities?.nodes?.length || 0 }}</div></div>
              <div class="cf-metric-card"><div class="cf-metric-label">关系数</div><div class="cf-after">{{ extractionResult.entities?.edges?.length || 0 }}</div></div>
              <div class="cf-metric-card"><div class="cf-metric-label">校验问题</div><div class="cf-detail" :class="extractionResult.validation?.is_clean ? 'positive' : 'zero'">{{ extractionResult.validation?.issue_count || 0 }}</div></div>
              <div class="cf-metric-card"><div class="cf-metric-label">模块覆盖率</div><div class="cf-after">{{ extractionResult.coverage?.module_coverage_pct || 0 }}%</div></div>
            </div>

            <div class="extraction-section" v-if="extractionResult.statistics?.module_distribution">
              <h4>📋 模块分布</h4>
              <div class="ext-module-list">
                <div v-for="(cnt, mod) in extractionResult.statistics.module_distribution" :key="mod" class="ext-module-row">
                  <span class="ext-mod-name">{{ mod }}</span>
                  <span class="ext-mod-bar-bg"><span class="ext-mod-bar" :style="{ width: (cnt / Math.max(...Object.values(extractionResult.statistics.module_distribution)) * 100) + '%' }"></span></span>
                  <span class="ext-mod-cnt">{{ cnt }}</span>
                </div>
              </div>
            </div>

            <div class="extraction-section">
              <h4>📋 难度分布</h4>
              <div class="ext-diff-row" v-for="(cnt, diff) in extractionResult.statistics?.difficulty_distribution" :key="diff">
                <span class="ext-diff-label">{{ '★'.repeat(parseInt(diff)) }}{{ '☆'.repeat(4 - parseInt(diff)) }}</span>
                <span class="ext-mod-bar-bg"><span class="ext-mod-bar diff-bar" :style="{ width: (cnt / Math.max(...Object.values(extractionResult.statistics.difficulty_distribution)) * 100) + '%' }"></span></span>
                <span class="ext-mod-cnt">{{ cnt }}</span>
              </div>
            </div>

            <div class="extraction-section" v-if="extractionResult.coverage?.covered_modules">
              <h4>✅ 已覆盖模块（{{ extractionResult.coverage.covered_module_count }}/{{ extractionResult.coverage.standard_module_count }}）</h4>
              <div class="tag-list">
                <span v-for="m in extractionResult.coverage.covered_modules" :key="m" class="tag tag-prereq">{{ m }}</span>
              </div>
              <h4 v-if="extractionResult.coverage.missing_modules?.length" style="margin-top:0.5rem;">❌ 缺失模块</h4>
              <div class="tag-list" v-if="extractionResult.coverage.missing_modules?.length">
                <span v-for="m in extractionResult.coverage.missing_modules" :key="m" class="tag tag-weak">{{ m }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 算法结果面板 -->
      <div v-if="showAlgorithms" ref="panelRef" class="algorithm-panel" :style="panelPos.x !== null ? { left: panelPos.x + 'px', top: panelPos.y + 'px', right: 'auto' } : {}">
        <div class="panel-header" @mousedown="startDrag" style="cursor: move; user-select: none;">
          <h3>网络科学算法</h3>
          <button class="close-btn" @click="showAlgorithms = false">×</button>
        </div>
        <div class="panel-content">
          <div class="algorithm-section">
            <h4>度中心性（Top 10）</h4>
            <div class="centrality-list">
              <div v-for="item in degreeCentrality" :key="item.id" class="centrality-item" @click="focusNode(item.id)">
                <span class="centrality-rank">{{ item.score.toFixed(4) }}</span>
                <span class="centrality-name">{{ item.name }}</span>
                <span class="centrality-module" :style="{ color: getModuleColor(item.module) }">{{ item.module }}</span>
              </div>
            </div>
          </div>
          <div class="algorithm-section">
            <h4>介数中心性（Top 10）</h4>
            <div class="centrality-list">
              <div v-for="item in betweennessCentrality" :key="item.id" class="centrality-item" @click="focusNode(item.id)">
                <span class="centrality-rank">{{ item.score.toFixed(4) }}</span>
                <span class="centrality-name">{{ item.name }}</span>
                <span class="centrality-module" :style="{ color: getModuleColor(item.module) }">{{ item.module }}</span>
              </div>
            </div>
          </div>
          <div class="algorithm-section">
            <h4>🌟 知识点影响力排名（PageRank Top 10）</h4>
            <div class="centrality-list">
              <div v-for="item in pagerankCentrality" :key="item.id" class="centrality-item" @click="focusNode(item.id)">
                <span class="centrality-rank">#{{ item.rank }}</span>
                <span class="centrality-name">{{ item.name }}</span>
                <span class="centrality-module" :style="{ color: getModuleColor(item.module) }">{{ item.module }}</span>
                <span class="centrality-score">PR={{ item.score.toFixed(4) }}</span>
              </div>
            </div>
            <div v-if="pagerankSummary" class="pagerank-summary">{{ pagerankSummary }}</div>
          </div>
          <div class="algorithm-section">
            <h4>社区发现（{{ communities.length }} 个社区）</h4>
            <div v-for="comm in communities" :key="comm.community_id" class="community-item">
              <div class="community-header">
                社区 {{ comm.community_id }} ({{ comm.size }} 个节点)
              </div>
              <div class="community-nodes">
                <span v-for="node in comm.nodes" :key="node.id" class="tag" @click="focusNode(node.id)">
                  {{ node.name }}
                </span>
              </div>
            </div>
            <!-- 社区对比 -->
            <div v-if="communityCompare" class="compare-section" style="margin-top:0.6rem;padding-top:0.6rem;border-top:1px dashed #eee;">
              <h4 style="font-size:0.85rem;margin-bottom:0.4rem;">自实现 Newman vs girvan_newman 对比</h4>
              <table class="compare-table">
                <tbody>
                <tr><th></th><th>自实现 Newman</th><th>girvan_newman</th></tr>
                <tr><td>模块度 Q</td><td>{{ communityCompare.custom?.modularity }}</td><td>{{ communityCompare.networkx?.modularity }}</td></tr>
                <tr><td>社区数</td><td>{{ communityCompare.custom?.count }}</td><td>{{ communityCompare.networkx?.count }}</td></tr>
                </tbody>
              </table>
              <p style="font-size:0.75rem;margin-top:0.3rem;">
                <span v-if="communityCompare.comparison?.custom_better" style="color:#52c41a;">✅ 自实现 Newman 优于 girvan_newman</span>
                <span v-else-if="communityCompare.comparison?.nx_better" style="color:#e67e22;">⚠️ girvan_newman 略优</span>
                <span v-else style="color:#888;">两者相当</span>
              </p>
            </div>
          </div>
          <div class="algorithm-section">
            <h4>学习路径规划</h4>
            <div class="path-input">
              <input v-model="pathStart" placeholder="起始节点ID" class="input-field" />
              <span>→</span>
              <input v-model="pathEnd" placeholder="目标节点ID" class="input-field" />
              <button class="btn" @click="findPath">最短路径</button>
              <button class="btn btn-adaptive" @click="findAdaptivePath" :disabled="!currentUser" title="基于边权重避开难点">加权路径</button>
            </div>
            <div v-if="shortestPath" class="path-result">
              <p v-if="shortestPath.total_weight !== undefined">
                加权距离：{{ shortestPath.total_weight.toFixed(2) }}｜路径长度：{{ shortestPath.length }} 步
              </p>
              <p v-else>路径长度：{{ shortestPath.length }} 步</p>
              <div class="path-nodes">
                <span v-for="(node, idx) in shortestPath.path" :key="node.id" class="path-node">
                  {{ node.name }}
                  <span v-if="idx < shortestPath.path.length - 1"> → </span>
                </span>
              </div>
            </div>
            <div class="weight-legend" v-if="currentUser && Object.keys(edgeWeights).length > 0">
              <span class="legend-item"><span class="legend-dot" style="background:#b0b0b0"></span>易</span>
              <span class="legend-item"><span class="legend-dot" style="background:#e67e22"></span>难</span>
              <span class="legend-item">边越粗 = 权重越高（越难）</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Day 6: 数据仪表盘 -->
    <div v-if="showDashboard" class="dashboard-section">
      <div class="dashboard-header">
        <h2>📊 学习数据仪表盘</h2>
        <div class="dashboard-controls">
          <button class="btn" @click="toggleDashboard">← 返回知识图谱</button>
          <button class="btn" @click="refreshDashboard">🔄 刷新数据</button>
          <span class="dashboard-user" v-if="currentUser">用户：{{ currentUser }}</span>
        </div>
      </div>
      <div class="dashboard-grid">
        <div class="dashboard-card card-module-mastery">
          <div class="card-header"><h3>模块掌握程度</h3></div>
          <div ref="barChartRef" class="chart-box"></div>
        </div>
        <div class="dashboard-card card-radar">
          <div class="card-header"><h3>模块掌握雷达图</h3></div>
          <div ref="radarChartRef" class="chart-box"></div>
        </div>
        <div class="dashboard-card card-weak">
          <div class="card-header"><h3>薄弱知识点分布</h3></div>
          <div ref="weakChartRef" class="chart-box"></div>
        </div>
        <div class="dashboard-card card-heatmap">
          <div class="card-header"><h3>知识状态热力图</h3></div>
          <div ref="heatmapChartRef" class="chart-box"></div>
        </div>
      </div>
    </div>

    <!-- Day 7: AI 问答面板 -->
    <div v-if="showChat" class="chat-panel">
      <div class="chat-header">
        <h3>🤖 AI 学习助手</h3>
        <button class="close-btn" @click="toggleChat">×</button>
      </div>
      <div class="chat-messages" ref="chatMessagesRef">
        <div v-if="chatMessages.length === 0" class="chat-welcome">
          <p>你好！我是你的 AI 学习助手。</p>
          <p>你可以问我任何高中数学问题，我会结合知识图谱为你解答。</p>
          <div class="chat-suggestions">
            <button v-for="(q, idx) in suggestedQuestions" :key="idx" class="suggestion-btn" @click="quickQuestion(q)">
              {{ q }}
            </button>
          </div>
        </div>
        <div v-for="(msg, idx) in chatMessages" :key="idx" class="chat-message" :class="msg.role">
          <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="msg-content">
            <div class="msg-text" v-html="renderMessage(msg.content)"></div>
            <div v-if="msg.related_nodes && msg.related_nodes.length > 0" class="msg-nodes">
              <span v-for="node in msg.related_nodes" :key="node.id" class="tag" :style="{ background: getModuleColor(node.module) }" @click="focusNode(node.id)">
                {{ node.name }}
              </span>
            </div>
          </div>
        </div>
        <div v-if="chatLoading && chatMessages.length > 0 && chatMessages[chatMessages.length-1].content === ''" class="chat-message assistant">
          <div class="msg-avatar">🤖</div>
          <div class="msg-content">
            <div class="msg-thinking">思考中...</div>
          </div>
        </div>
      </div>
      <div class="chat-input-area">
        <input v-model="chatInput" @keydown.enter="handleSendChat" placeholder="输入你的数学问题..." class="chat-input" :disabled="chatLoading" />
        <button class="btn btn-send" @click="handleSendChat" :disabled="chatLoading || !chatInput.trim()">
          {{ chatLoading ? '...' : '发送' }}
        </button>
      </div>
      <div v-if="chatRelatedNodes.length > 0" class="chat-related">
        <span class="related-label">关联知识点：</span>
        <span v-for="node in chatRelatedNodes" :key="node.id" class="tag" :style="{ background: getModuleColor(node.module) }" @click="focusNode(node.id)">
          {{ node.name }}
        </span>
      </div>
    </div>

    <!-- 智能诊断面板 -->
    <div v-if="showDiagnosis" ref="diagnosisPanelRef" class="diagnosis-panel" :style="diagnosisPanelPos.x !== null ? { left: diagnosisPanelPos.x + 'px', top: diagnosisPanelPos.y + 'px', right: 'auto' } : {}">
      <div class="panel-header" @mousedown="startDiagnosisDrag">
        <h3>智能诊断报告</h3>
        <button class="close-btn" @click="showDiagnosis = false">×</button>
      </div>
      <div class="panel-content" v-if="diagnosisLoading">
        <div class="loading-spinner"></div>
        <p>正在分析学习状况...</p>
      </div>
      <div class="panel-content" v-else-if="diagnosisResult">
        <div class="diagnosis-summary">
          <div class="summary-item">
            <span class="summary-number">{{ diagnosisResult.summary.total_weak_points }}</span>
            <span class="summary-label">薄弱点</span>
          </div>
          <div class="summary-item">
            <span class="summary-number">{{ diagnosisResult.summary.total_missing_prerequisites }}</span>
            <span class="summary-label">缺失前置</span>
          </div>
          <div class="summary-item">
            <span class="summary-number">{{ diagnosisResult.summary.nodes_with_missing_prerequisites }}</span>
            <span class="summary-label">待补节点</span>
          </div>
        </div>

        <!-- 模块掌握度 -->
        <div class="diagnosis-section" v-if="userModel && userModel.module_mastery">
          <h4>模块掌握度
            <span class="overall-pct">总体 {{ userModel.user_stats.mastery_pct }}%</span>
          </h4>
          <div class="module-mastery-list">
            <div v-for="m in userModel.module_mastery" :key="m.module" class="module-mastery-item">
              <div class="module-mastery-header">
                <span class="module-name">{{ m.module }}</span>
                <span class="module-count">{{ m.mastered }}/{{ m.total }}</span>
                <span class="module-status-tag" :class="'status-' + m.status">{{ m.mastery_pct }}%</span>
              </div>
              <div class="mastery-bar-bg">
                <div class="mastery-bar-fill" 
                     :style="{ width: m.mastery_pct + '%',
                              background: m.mastery_pct >= 80 ? '#52c41a' : m.mastery_pct >= 40 ? '#faad14' : '#f5222d' }">
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="diagnosis-section" v-if="diagnosisResult.weak_points.length > 0">
          <h4>薄弱知识点</h4>
          <div class="weak-list">
            <div v-for="wp in diagnosisResult.weak_points" :key="wp.id" class="weak-item" @click="focusNode(wp.id)">
              <span class="weak-name">{{ wp.name }}</span>
              <span class="weak-module" :style="{ color: getModuleColor(wp.module) }">{{ wp.module }}</span>
            </div>
          </div>
        </div>

        <div class="diagnosis-section" v-if="Object.keys(diagnosisResult.missing_prerequisites).length > 0">
          <h4>缺失的前置知识</h4>
          <div v-for="(data, nodeId) in diagnosisResult.missing_prerequisites" :key="nodeId" class="missing-section">
            <p class="missing-title">{{ data.name }} 需要：</p>
            <div class="missing-list">
              <span v-for="item in data.missing" :key="item.id" class="tag tag-missing" @click="focusNode(item.id)">
                {{ item.name }}
                <span class="status-mini">{{ getStatusText(item.status) }}</span>
              </span>
            </div>
          </div>
        </div>

        <div class="diagnosis-actions">
          <button class="btn" @click="showDailySuggestions = true; showDiagnosis = false">
            查看学习建议
          </button>
        </div>
      </div>
    </div>

    <!-- 每日学习建议面板 -->
    <div v-if="showDailySuggestions && dailySuggestions.length > 0" ref="suggestionPanelRef" class="suggestion-panel" :style="suggestionPanelPos.x !== null ? { left: suggestionPanelPos.x + 'px', top: suggestionPanelPos.y + 'px', right: 'auto' } : {}">
      <div class="panel-header" @mousedown="startSuggestionDrag">
        <h3>📚 每日学习建议</h3>
        <button class="close-btn" @click="showDailySuggestions = false">×</button>
      </div>
      <div class="panel-content">
        <div v-for="(suggestion, idx) in dailySuggestions" :key="idx" class="suggestion-group">
          <h4>{{ suggestion.title }}</h4>
          <div class="suggestion-items">
            <div v-for="item in suggestion.items" :key="item.id" class="suggestion-item" @click="focusNode(item.id)">
              <span class="suggestion-name">{{ item.name }}</span>
              <span class="suggestion-module" :style="{ color: getModuleColor(item.module) }">{{ item.module }}</span>
              <button class="btn btn-sm" @click.stop="getLearningPath(item.id)" :disabled="learningPathLoading">
                学习路径
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 学习路径显示 -->
    <div v-if="learningPath" class="learning-path-panel">
      <div class="panel-header">
        <h3>🎯 学习路径：{{ learningPath.target.name }}</h3>
        <button class="close-btn" @click="clearLearningPath">×</button>
      </div>
      <div class="panel-content" v-if="learningPathLoading">
        <div class="loading-spinner"></div>
        <p>正在生成学习路径...</p>
      </div>
      <div class="panel-content" v-else>
        <div class="path-stats">
          <span>总步骤：{{ learningPath.statistics.total_steps }}</span>
          <span>已掌握：{{ learningPath.statistics.mastered }}</span>
          <span>需学习：{{ learningPath.statistics.needs_learning }}</span>
        </div>
        <div class="path-sequence">
          <div v-for="(step, idx) in learningPath.path" :key="step.id" class="path-step" :class="{
            'step-mastered': step.is_mastered,
            'step-weak': step.is_weak,
            'step-unlearned': step.is_unlearned
          }">
            <span class="step-number">{{ idx + 1 }}</span>
            <span class="step-name">{{ step.name }}</span>
            <span class="step-status">{{ getStatusText(step.status) }}</span>
            <span v-if="idx < learningPath.path.length - 1" class="step-arrow">→</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 网络科学综合分析 -->
    <div v-if="showNetworkAnalysis" ref="networkPanelRef" class="network-analysis-panel" :style="networkPanelPos.x !== null ? { left: networkPanelPos.x + 'px', top: networkPanelPos.y + 'px', right: 'auto' } : {}">
      <div class="panel-header" @mousedown="startNetworkDrag" style="cursor:move;user-select:none">
        <h3>📈 网络科学综合分析</h3>
        <button class="close-btn" @click="showNetworkAnalysis = false">×</button>
      </div>
      <div class="panel-content" v-if="networkAnalysisLoading">
        <div class="loading-spinner"></div>
        <p>正在分析网络结构...</p>
      </div>
      <div class="panel-content" v-else-if="networkAnalysis">
        <!-- 基本统计 -->
        <div class="analysis-section">
          <h4>📊 基本统计</h4>
          <table class="stats-table" v-if="networkAnalysis.basic_stats">
            <tbody>
            <tr><td>节点总数</td><td>{{ networkAnalysis.basic_stats.node_count }}</td>
                <td>边总数</td><td>{{ networkAnalysis.basic_stats.edge_count }}</td></tr>
            <tr><td>平均出度</td><td>{{ networkAnalysis.basic_stats.avg_out_degree }}</td>
                <td>平均入度</td><td>{{ networkAnalysis.basic_stats.avg_in_degree }}</td></tr>
            <tr><td>最大出度</td><td>{{ networkAnalysis.basic_stats.max_out_degree }}</td>
                <td>最大入度</td><td>{{ networkAnalysis.basic_stats.max_in_degree }}</td></tr>
            <tr><td>网络直径</td><td>{{ networkAnalysis.basic_stats.diameter ?? 'N/A' }}</td>
                <td>图密度</td><td>{{ networkAnalysis.basic_stats.density }}</td></tr>
            <tr><td>平均路径长度</td><td>{{ networkAnalysis.basic_stats.avg_path_length ?? 'N/A' }}</td>
                <td>模块数</td><td>{{ networkAnalysis.basic_stats.module_count }}</td></tr>
            <tr><td>最多节点模块</td><td>{{ networkAnalysis.basic_stats.max_module_name }}({{ networkAnalysis.basic_stats.max_module_nodes }})</td>
                <td>最少节点模块</td><td>{{ networkAnalysis.basic_stats.min_module_name }}({{ networkAnalysis.basic_stats.min_module_nodes }})</td></tr>
            <tr><td>自实现 Newman Q</td><td>{{ networkAnalysis.basic_stats.modularity_custom ?? 'N/A' }}</td>
                <td>Girvan-Newman Q</td><td>{{ networkAnalysis.basic_stats.modularity_girvan_newman ?? 'N/A' }}</td></tr>
            </tbody>
          </table>
        </div>
        <!-- 无标度 -->
        <div class="analysis-section">
          <h4>① 无标度网络分析</h4>
          <div ref="scaleFreeChartRef" style="height:220px"></div>
          <table class="fit-table" v-if="networkAnalysis.scale_free.in_power_law">
            <tbody>
            <tr><th></th><th>入度</th><th>出度</th></tr>
            <tr><td>幂律指数 α</td><td>{{ networkAnalysis.scale_free.in_power_law.alpha }}</td><td>{{ networkAnalysis.scale_free.out_power_law.alpha }}</td></tr>
            <tr><td>KS 统计量</td><td>{{ networkAnalysis.scale_free.in_power_law.ks_stat }}</td><td>{{ networkAnalysis.scale_free.out_power_law.ks_stat }}</td></tr>
            <tr><td>xmin</td><td>{{ networkAnalysis.scale_free.in_power_law.xmin }}</td><td>{{ networkAnalysis.scale_free.out_power_law.xmin }}</td></tr>
            </tbody>
          </table>
          <div v-if="networkAnalysis.scale_free.hub_nodes_in.length" class="hub-list">
            <span class="hub-label">入度最大的知识点：</span>
            <span v-for="h in networkAnalysis.scale_free.hub_nodes_in" :key="h.id" class="tag" @click="focusNode(h.id)">{{ h.name }}(入度{{ h.degree }})</span>
          </div>
          <div v-if="networkAnalysis.scale_free.hub_nodes_out.length" class="hub-list">
            <span class="hub-label">出度最大的知识点：</span>
            <span v-for="h in networkAnalysis.scale_free.hub_nodes_out" :key="h.id" class="tag" @click="focusNode(h.id)">{{ h.name }}(出度{{ h.degree }})</span>
          </div>
          <p class="analysis-summary">{{ networkAnalysis.scale_free.summary }}</p>
        </div>
        <!-- 小世界 -->
        <div class="analysis-section">
          <h4>② 小世界特性</h4>
          <div ref="smallWorldChartRef" style="height:240px"></div>
          <p class="analysis-summary">{{ networkAnalysis.small_world.summary }}</p>
        </div>
        <!-- 鲁棒性 -->
        <div class="analysis-section">
          <h4>③ 网络鲁棒性</h4>
          <div ref="robustnessChartRef" style="height:240px"></div>
          <p class="analysis-summary">{{ networkAnalysis.robustness.summary }}</p>
        </div>
        <!-- 影响力最大化 -->
        <div class="analysis-section">
          <h4>④ 影响力最大化</h4>
          <div ref="influenceChartRef" style="height:220px"></div>
          <div class="seed-list" v-if="networkAnalysis.influence.seeds.length">
            <span class="hub-label">贪心选出的 top-5 种子知识点：</span>
            <span v-for="s in networkAnalysis.influence.seeds" :key="s.id" class="tag tag-seed" @click="focusNode(s.id)">
              #{{ s.rank }} {{ s.name }} (覆盖{{ s.influence_spread }})
            </span>
          </div>
          <p class="analysis-summary">{{ networkAnalysis.influence.summary }}</p>
        </div>
      </div>
    </div>

    <!-- 混合推荐面板 -->
    <div v-if="showHybrid" ref="hybridPanelRef" class="hybrid-panel" :style="hybridPanelPos.x !== null ? { left: hybridPanelPos.x + 'px', top: hybridPanelPos.y + 'px', right: 'auto' } : {}">
      <div class="panel-header" @mousedown="startHybridDrag" style="cursor:move;user-select:none">
        <h3>🎯 混合推荐</h3>
        <button class="close-btn" @click="showHybrid = false">×</button>
      </div>
      <div class="panel-content" v-if="hybridLoading">
        <div class="loading-spinner"></div>
        <p>正在生成推荐...</p>
      </div>
      <div class="panel-content" v-else-if="hybridResult">
        <div ref="hybridChartRef" style="height:200px"></div>
        <p class="analysis-summary">{{ hybridResult.explanation }}</p>
        <div v-if="hybridResult.recommendations.length" class="hybrid-list">
          <div v-for="(r, i) in hybridResult.recommendations" :key="r.id" class="hybrid-item" @click="focusNode(r.id)">
            <span class="hybrid-rank">#{{ i + 1 }}</span>
            <div class="hybrid-info">
              <span class="hybrid-name">{{ r.name }}</span>
              <span class="hybrid-module" :style="{ color: getModuleColor(r.module) }">{{ r.module }}</span>
              <span class="hybrid-status" :class="'status-' + r.status">{{ getStatusText(r.status) }}</span>
            </div>
            <div class="hybrid-scores">
              <span class="score-bar" title="图算法重要性">
                <span class="score-fill score-graph" :style="{ width: r.graph_score * 100 + '%' }"></span>
              </span>
              <span class="score-bar" title="相似用户经验">
                <span class="score-fill score-cf" :style="{ width: r.cf_score * 100 + '%' }"></span>
              </span>
              <span class="score-bar" title="知识点关联分析">
                <span class="score-fill score-llm" :style="{ width: r.llm_score * 100 + '%' }"></span>
              </span>
            </div>
          </div>
        </div>
        <div v-else>
          <p>暂无推荐</p>
        </div>
      </div>
    </div>

    <!-- 登录/注册对话框 -->
    <div v-if="showLoginDialog" class="modal-overlay" @click.self="showLoginDialog = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ isRegister ? '注册' : '登录' }}</h3>
          <button class="close-btn" @click="showLoginDialog = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="loginUsername" placeholder="请输入用户名" class="input-field" />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input v-model="loginPassword" type="password" placeholder="请输入密码" class="input-field" />
          </div>
          <button class="btn btn-block" @click="isRegister ? handleRegister() : handleLogin()">
            {{ isRegister ? '注册' : '登录' }}
          </button>
          <p class="form-switch">
            {{ isRegister ? '已有账号？' : '没有账号？' }}
            <a href="javascript:void(0)" @click="isRegister = !isRegister">{{ isRegister ? '去登录' : '去注册' }}</a>
          </p>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>正在构建知识网络...</p>
    </div>

    <!-- 注销确认弹窗 -->
    <div v-if="showDeregisterConfirm" class="modal-overlay" @click.self="showDeregisterConfirm = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>确认注销</h3>
          <button class="close-btn" @click="showDeregisterConfirm = false">×</button>
        </div>
        <div class="modal-body">
          <p style="margin-bottom:1rem;color:#f5222d">⚠️ 注销后所有学习数据将被永久删除，此操作不可恢复！</p>
          <button class="btn btn-block btn-danger" @click="handleDeregister">确认注销</button>
          <button class="btn btn-block" style="margin-top:0.5rem" @click="showDeregisterConfirm = false">取消</button>
        </div>
      </div>
    </div>
    <div v-if="errorMsg" class="error-overlay">
      <p>{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getKnowledgeNetwork, getNodeDetail, getDegreeCentrality, getBetweennessCentrality, getPageRank, getCommunity, getCommunityCompare, getCommunityExplain, getShortestPath, diagnoseWeakPoints, recommendLearningPath, sendChatMessage as sendChatMessageApi, sendChatMessageStream, getEdgeWeights, updateEdgeWeight, applyProgressToWeights, getAdaptivePath, getUserModel, deleteUser, getNetworkAnalysis, getHybridRecommend, getCounterfactual, getKGTriples, getTransitiveClosure, getRuleReasoning, getKGQuery, runEntityExtraction, getEntityStatistics } from '../api'

const chartRef = ref(null)
const cfPanelRef = ref(null)
const modules = ref([])
const nodesData = ref([])
const edgesData = ref([])
const loading = ref(true)
const selectedNode = ref(null)
const nodeDetail = ref(null)
const showLabels = ref(true)
const errorMsg = ref('')
const isFullscreen = ref(false)

// 用户相关
const currentUser = ref(null)
const showLoginDialog = ref(false)
const loginUsername = ref('')
const loginPassword = ref('')
const isRegister = ref(false)

// 学习进度
const progressData = ref({}) // nodeId -> status

// 算法结果
const degreeCentrality = ref([])
const betweennessCentrality = ref([])
const pagerankCentrality = ref([])
const pagerankSummary = ref('')
const communities = ref([])
const communityCompare = ref(null)
const communityExplain = ref(null)
const communityExplainLoading = ref(false)
const shortestPath = ref(null)
const showAlgorithms = ref(false)
const showGraph = ref(true)
const pathStart = ref('')
const pathEnd = ref('')
const edgeWeights = ref({})  // "from-to" -> weight

const getEdgeWeight = (from, to) => {
  const key = `${from}-${to}`
  return edgeWeights.value[key] ?? 1.0
}

const getEdgeWidth = (from, to) => {
  const w = getEdgeWeight(from, to)
  return Math.max(1, Math.min(8, w * 2))
}

// Day 5: 智能诊断 & 路径推荐
const showDiagnosis = ref(false)
const diagnosisResult = ref(null)
const diagnosisLoading = ref(false)
const userModel = ref(null)
const learningPath = ref(null)
const learningPathLoading = ref(false)
const dailySuggestions = ref([])
const showDailySuggestions = ref(false)

// Day 6: 统计图表 & 热力图
const showDashboard = ref(false)
const barChartRef = ref(null)
const radarChartRef = ref(null)
const weakChartRef = ref(null)
const heatmapChartRef = ref(null)
const dashboardCharts = []

// 网络科学综合分析
const showNetworkAnalysis = ref(false)
const networkAnalysis = ref(null)
const networkAnalysisLoading = ref(false)
const scaleFreeChartRef = ref(null)
const robustnessChartRef = ref(null)
const influenceChartRef = ref(null)
const smallWorldChartRef = ref(null)
const networkCharts = []

// 反事实推理
const showCounterfactual = ref(false)
const counterfactualResult = ref(null)
const counterfactualLoading = ref(false)
const counterfactualSimStatus = ref("mastered")

const runCounterfactual = async () => {
  if (!selectedNode.value) return
  counterfactualLoading.value = true
  try {
    const data = await getCounterfactual(
      currentUser.value?.id || '',
      progressData.value,
      selectedNode.value.id,
      counterfactualSimStatus.value
    )
    counterfactualResult.value = data
    showCounterfactual.value = true
  } catch (e) {
    console.error('反事实推理失败:', e)
  } finally {
    counterfactualLoading.value = false
  }
}

// 三元组浏览
const showTriples = ref(false)
const triplesData = ref([])
const triplesLoading = ref(false)
const triplesRelationFilter = ref("全部")
const allTriplesCount = ref(0)

const triplesPanelRef = ref(null)
const triplesPanelPos = ref({ x: null, y: null })
const triplesIsDragging = ref(false)
const triplesDragOffset = ref({ x: 0, y: 0 })

const startTriplesDrag = (e) => {
  if (!triplesPanelRef.value) return
  const rect = triplesPanelRef.value.getBoundingClientRect()
  if (triplesPanelPos.value.x === null) {
    triplesPanelPos.value.x = rect.left
    triplesPanelPos.value.y = rect.top
  }
  triplesDragOffset.value.x = e.clientX - rect.left
  triplesDragOffset.value.y = e.clientY - rect.top
  triplesIsDragging.value = true
  document.addEventListener('mousemove', onTriplesDrag)
  document.addEventListener('mouseup', stopTriplesDrag)
  e.preventDefault()
}

const onTriplesDrag = (e) => {
  if (!triplesIsDragging.value) return
  triplesPanelPos.value.x = e.clientX - triplesDragOffset.value.x
  triplesPanelPos.value.y = e.clientY - triplesDragOffset.value.y
}

const stopTriplesDrag = () => {
  triplesIsDragging.value = false
  document.removeEventListener('mousemove', onTriplesDrag)
  document.removeEventListener('mouseup', stopTriplesDrag)
}

// 诊断面板拖拽
const diagnosisPanelRef = ref(null)
const diagnosisPanelPos = ref({ x: null, y: null })
const diagnosisIsDragging = ref(false)
const diagnosisDragOffset = ref({ x: 0, y: 0 })

const startDiagnosisDrag = (e) => {
  if (!diagnosisPanelRef.value) return
  const rect = diagnosisPanelRef.value.getBoundingClientRect()
  if (diagnosisPanelPos.value.x === null) {
    diagnosisPanelPos.value.x = rect.left
    diagnosisPanelPos.value.y = rect.top
  }
  diagnosisDragOffset.value.x = e.clientX - rect.left
  diagnosisDragOffset.value.y = e.clientY - rect.top
  diagnosisIsDragging.value = true
  document.addEventListener('mousemove', onDiagnosisDrag)
  document.addEventListener('mouseup', stopDiagnosisDrag)
  e.preventDefault()
}
const onDiagnosisDrag = (e) => {
  if (!diagnosisIsDragging.value) return
  diagnosisPanelPos.value.x = e.clientX - diagnosisDragOffset.value.x
  diagnosisPanelPos.value.y = e.clientY - diagnosisDragOffset.value.y
}
const stopDiagnosisDrag = () => {
  diagnosisIsDragging.value = false
  document.removeEventListener('mousemove', onDiagnosisDrag)
  document.removeEventListener('mouseup', stopDiagnosisDrag)
}

// 建议面板拖拽
const suggestionPanelRef = ref(null)
const suggestionPanelPos = ref({ x: null, y: null })
const suggestionIsDragging = ref(false)
const suggestionDragOffset = ref({ x: 0, y: 0 })

const startSuggestionDrag = (e) => {
  if (!suggestionPanelRef.value) return
  const rect = suggestionPanelRef.value.getBoundingClientRect()
  if (suggestionPanelPos.value.x === null) {
    suggestionPanelPos.value.x = rect.left
    suggestionPanelPos.value.y = rect.top
  }
  suggestionDragOffset.value.x = e.clientX - rect.left
  suggestionDragOffset.value.y = e.clientY - rect.top
  suggestionIsDragging.value = true
  document.addEventListener('mousemove', onSuggestionDrag)
  document.addEventListener('mouseup', stopSuggestionDrag)
  e.preventDefault()
}
const onSuggestionDrag = (e) => {
  if (!suggestionIsDragging.value) return
  suggestionPanelPos.value.x = e.clientX - suggestionDragOffset.value.x
  suggestionPanelPos.value.y = e.clientY - suggestionDragOffset.value.y
}
const stopSuggestionDrag = () => {
  suggestionIsDragging.value = false
  document.removeEventListener('mousemove', onSuggestionDrag)
  document.removeEventListener('mouseup', stopSuggestionDrag)
}

const loadTriples = async () => {
  triplesLoading.value = true
  try {
    const rel = triplesRelationFilter.value === "全部" ? null : triplesRelationFilter.value
    const data = await getKGTriples(rel)
    triplesData.value = data.triples || []
    if (!rel) allTriplesCount.value = data.total || 0
    showTriples.value = true
  } catch (e) {
    console.error('加载三元组失败:', e)
  } finally {
    triplesLoading.value = false
  }
}

// 语义推理
const showReasoning = ref(false)
const reasoningLoading = ref(false)
const reasoningResult = ref(null)
const reasoningRule = ref("transitive_prerequisite")
const reasoningSourceId = ref("")
const reasoningTargetId = ref("")
const reasoningPanelRef = ref(null)
const reasoningPanelPos = ref({ x: null, y: null })
const reasoningIsDragging = ref(false)
const reasoningDragOffset = ref({ x: 0, y: 0 })

const startReasoningDrag = (e) => {
  if (!reasoningPanelRef.value) return
  const rect = reasoningPanelRef.value.getBoundingClientRect()
  if (reasoningPanelPos.value.x === null) { reasoningPanelPos.value.x = rect.left; reasoningPanelPos.value.y = rect.top }
  reasoningDragOffset.value.x = e.clientX - rect.left
  reasoningDragOffset.value.y = e.clientY - rect.top
  reasoningIsDragging.value = true
  document.addEventListener('mousemove', onReasoningDrag)
  document.addEventListener('mouseup', stopReasoningDrag)
  e.preventDefault()
}
const onReasoningDrag = (e) => { if (!reasoningIsDragging.value) return; reasoningPanelPos.value.x = e.clientX - reasoningDragOffset.value.x; reasoningPanelPos.value.y = e.clientY - reasoningDragOffset.value.y }
const stopReasoningDrag = () => { reasoningIsDragging.value = false; document.removeEventListener('mousemove', onReasoningDrag); document.removeEventListener('mouseup', stopReasoningDrag) }

const loadReasoning = async () => {
  reasoningLoading.value = true
  reasoningResult.value = null
  try {
    if (reasoningRule.value === "transitive_prerequisite") {
      const nid = selectedNode.value?.id || parseInt(reasoningSourceId.value)
      if (!nid) { reasoningLoading.value = false; return }
      const data = await getRuleReasoning("transitive_prerequisite", { node_id: nid })
      reasoningResult.value = data
    } else if (reasoningRule.value === "mastery_impact") {
      const nid = selectedNode.value?.id || parseInt(reasoningSourceId.value)
      if (!nid) { reasoningLoading.value = false; return }
      const data = await getRuleReasoning("mastery_impact", { node_id: nid, progress: progressData.value })
      reasoningResult.value = data
    } else if (reasoningRule.value === "all_paths") {
      const sid = parseInt(reasoningSourceId.value)
      const tid = parseInt(reasoningTargetId.value)
      if (!sid || !tid) { reasoningLoading.value = false; return }
      const data = await getRuleReasoning("all_paths", { source_id: sid, target_id: tid })
      reasoningResult.value = data
    } else if (reasoningRule.value === "transitive_closure") {
      const nid = selectedNode.value?.id || parseInt(reasoningSourceId.value)
      if (!nid) { reasoningLoading.value = false; return }
      const data = await getTransitiveClosure(nid)
      reasoningResult.value = data
    }
  } catch (e) {
    console.error('推理失败:', e)
  } finally {
    reasoningLoading.value = false
  }
}

// 语义检索
const showKGSearch = ref(false)
const searchLoading = ref(false)
const searchResults = ref([])
const searchTotal = ref(0)
const searchQuery = ref({ name: '', module: '', difficulty_min: null, difficulty_max: null })
const searchPanelRef = ref(null)
const searchPanelPos = ref({ x: null, y: null })
const searchIsDragging = ref(false)
const searchDragOffset = ref({ x: 0, y: 0 })

const startSearchDrag = (e) => {
  if (!searchPanelRef.value) return
  const rect = searchPanelRef.value.getBoundingClientRect()
  if (searchPanelPos.value.x === null) { searchPanelPos.value.x = rect.left; searchPanelPos.value.y = rect.top }
  searchDragOffset.value.x = e.clientX - rect.left
  searchDragOffset.value.y = e.clientY - rect.top
  searchIsDragging.value = true
  document.addEventListener('mousemove', onSearchDrag)
  document.addEventListener('mouseup', stopSearchDrag)
  e.preventDefault()
}
const onSearchDrag = (e) => { if (!searchIsDragging.value) return; searchPanelPos.value.x = e.clientX - searchDragOffset.value.x; searchPanelPos.value.y = e.clientY - searchDragOffset.value.y }
const stopSearchDrag = () => { searchIsDragging.value = false; document.removeEventListener('mousemove', onSearchDrag); document.removeEventListener('mouseup', stopSearchDrag) }

const loadKGSearch = async () => {
  searchLoading.value = true
  try {
    const q = {
      name: searchQuery.value.name || undefined,
      module: searchQuery.value.module || undefined,
      difficulty_min: searchQuery.value.difficulty_min || undefined,
      difficulty_max: searchQuery.value.difficulty_max || undefined
    }
    const data = await getKGQuery(q)
    searchResults.value = data.results || []
    searchTotal.value = data.total || 0
    showKGSearch.value = true
  } catch (e) {
    console.error('语义检索失败:', e)
  } finally {
    searchLoading.value = false
  }
}

const focusSearchNode = (id) => { focusNode(id) }

// 实体抽取
const showExtraction = ref(false)
const extractionLoading = ref(false)
const extractionResult = ref(null)
const extractionPanelRef = ref(null)
const extractionPanelPos = ref({ x: null, y: null })
const extractionIsDragging = ref(false)
const extractionDragOffset = ref({ x: 0, y: 0 })

const startExtractionDrag = (e) => {
  if (!extractionPanelRef.value) return
  const rect = extractionPanelRef.value.getBoundingClientRect()
  if (extractionPanelPos.value.x === null) { extractionPanelPos.value.x = rect.left; extractionPanelPos.value.y = rect.top }
  extractionDragOffset.value.x = e.clientX - rect.left
  extractionDragOffset.value.y = e.clientY - rect.top
  extractionIsDragging.value = true
  document.addEventListener('mousemove', onExtractionDrag)
  document.addEventListener('mouseup', stopExtractionDrag)
  e.preventDefault()
}
const onExtractionDrag = (e) => { if (!extractionIsDragging.value) return; extractionPanelPos.value.x = e.clientX - extractionDragOffset.value.x; extractionPanelPos.value.y = e.clientY - extractionDragOffset.value.y }
const stopExtractionDrag = () => { extractionIsDragging.value = false; document.removeEventListener('mousemove', onExtractionDrag); document.removeEventListener('mouseup', stopExtractionDrag) }

const loadExtraction = async () => {
  extractionLoading.value = true
  try {
    const data = await runEntityExtraction()
    extractionResult.value = data
  } catch (e) {
    console.error('实体抽取失败:', e)
  } finally {
    extractionLoading.value = false
  }
}

const loadNetworkAnalysis = async () => {
  networkAnalysisLoading.value = true
  networkCharts.forEach(c => { try { c.dispose() } catch {} })
  networkCharts.length = 0
  try {
    const data = await getNetworkAnalysis()
    networkAnalysis.value = data
    networkAnalysisLoading.value = false
    await nextTick()
    renderScaleFreeChart(data.scale_free)
    renderSmallWorldChart(data.small_world)
    renderRobustnessChart(data.robustness)
    renderInfluenceChart(data.influence)
  } catch (e) {
    console.error('网络科学分析失败:', e)
    networkAnalysisLoading.value = false
  }
}

const renderScaleFreeChart = (data) => {
  const el = scaleFreeChartRef.value
  if (!el || !data) return
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: '度分布 (双对数)', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['入度', '出度'], top: 30 },
    grid: { left: 50, right: 20, top: 60, bottom: 40 },
    xAxis: { type: 'value', name: '度 (log)', logBase: 10, min: 1 },
    yAxis: { type: 'value', name: '节点数 (log)', logBase: 10, min: 1 },
    series: [
      {
        name: '入度', type: 'scatter',
        data: data.in_degree_dist.filter(d => d.degree > 0).map(d => [d.degree, d.count]),
        symbolSize: 8, itemStyle: { color: '#667eea' }
      },
      {
        name: '出度', type: 'scatter',
        data: data.out_degree_dist.filter(d => d.degree > 0).map(d => [d.degree, d.count]),
        symbolSize: 8, itemStyle: { color: '#e67e22' }
      }
    ]
  })
  networkCharts.push(chart)
}

const renderSmallWorldChart = (data) => {
  const el = smallWorldChartRef.value
  if (!el || !data) return
  const chart = echarts.init(el)
  const rl = data.real_network
  const rd = data.random_network
  const sigma = data.sigma
  const isSW = data.is_small_world
  chart.setOption({
    title: {
      text: '小世界特性对比',
      subtext: `σ = ${sigma}  ${isSW ? '✅ 具有小世界特性' : '❌ 不具有小世界特性'}`,
      left: 'center', textStyle: { fontSize: 14 }, subtextStyle: { fontSize: 12, color: isSW ? '#52c41a' : '#999' }
    },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['真实网络', '等价随机图'], top: 55 },
    grid: { left: 60, right: 30, top: 90, bottom: 30 },
    xAxis: {
      type: 'category',
      data: ['平均路径长度', '聚类系数'],
      axisLabel: { fontSize: 13, fontWeight: 'bold' }
    },
    yAxis: { type: 'value', name: '' },
    series: [
      {
        name: '真实网络',
        type: 'bar',
        data: [
          { value: rl.avg_path_length, itemStyle: { color: '#667eea', borderRadius: [6,6,0,0] } },
          { value: rl.clustering_coefficient, itemStyle: { color: '#667eea', borderRadius: [6,6,0,0] } }
        ],
        barWidth: '28%',
        label: { show: true, position: 'top', formatter: (p) => p.value.toFixed(4), fontSize: 11, color: '#667eea' }
      },
      {
        name: '等价随机图',
        type: 'bar',
        data: [
          { value: rd.avg_path_length, itemStyle: { color: '#e67e22', borderRadius: [6,6,0,0] } },
          { value: rd.clustering_coefficient, itemStyle: { color: '#e67e22', borderRadius: [6,6,0,0] } }
        ],
        barWidth: '28%',
        label: { show: true, position: 'top', formatter: (p) => p.value.toFixed(4), fontSize: 11, color: '#e67e22' }
      }
    ]
  })
  networkCharts.push(chart)
}

const renderRobustnessChart = (data) => {
  const el = robustnessChartRef.value
  if (!el || !data) return
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: '网络鲁棒性分析', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis' },
    legend: { data: ['随机攻击', '蓄意攻击'], top: 30 },
    grid: { left: 55, right: 20, top: 60, bottom: 40 },
    xAxis: { type: 'value', name: '移除节点比例 (%)' },
    yAxis: { type: 'value', name: '最大连通子图占比 (%)', min: 0, max: 100 },
    series: [
      {
        name: '随机攻击', type: 'line',
        data: data.random_attack.map(d => [d.removed_pct, d.largest_component_pct]),
        smooth: true, lineStyle: { color: '#52c41a', width: 2 },
        areaStyle: { color: 'rgba(82,196,26,0.15)' },
        symbol: 'circle'
      },
      {
        name: '蓄意攻击', type: 'line',
        data: data.targeted_attack.map(d => [d.removed_pct, d.largest_component_pct]),
        smooth: true, lineStyle: { color: '#f5222d', width: 2 },
        areaStyle: { color: 'rgba(245,34,45,0.15)' },
        symbol: 'diamond'
      }
    ]
  })
  networkCharts.push(chart)
}

const renderInfluenceChart = (data) => {
  const el = influenceChartRef.value
  if (!el || !data) return
  const chart = echarts.init(el)
  chart.setOption({
    title: { text: '影响力最大化策略对比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 60, right: 20, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: ['贪心算法', '高度数', 'PageRank'] },
    yAxis: { type: 'value', name: '预期影响力 (覆盖节点数)' },
    series: [{
      type: 'bar',
      data: [
        { value: data.greedy_spread, itemStyle: { color: '#667eea' } },
        { value: data.degree_spread, itemStyle: { color: '#52c41a' } },
        { value: data.pagerank_spread, itemStyle: { color: '#e67e22' } }
      ],
      barWidth: '50%',
      label: { show: true, position: 'top', formatter: '{c}' }
    }]
  })
  networkCharts.push(chart)
}

// 混合推荐
const showHybrid = ref(false)
const hybridResult = ref(null)
const hybridLoading = ref(false)
const hybridChartRef = ref(null)

const loadHybrid = async () => {
  if (!currentUser.value) return
  hybridLoading.value = true
  try {
    const users = loadUsers()
    const allProgress = {}
    for (const u of users) {
      if (u.progress) allProgress[u.username] = u.progress
    }
    const data = await getHybridRecommend(currentUser.value, progressData.value, allProgress)
    hybridResult.value = data
    await nextTick()
    renderHybridChart(data)
  } catch (e) {
    console.error('混合推荐失败:', e)
  } finally {
    hybridLoading.value = false
  }
}

const renderHybridChart = (data) => {
  const el = hybridChartRef.value
  if (!el || !data) return
  const chart = echarts.init(el)
  const c = data.contribution
  chart.setOption({
    title: { text: '推荐来源贡献占比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { trigger: 'item', formatter: '{b}: {c}% ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '55%'],
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 13 },
      emphasis: { label: { fontSize: 16, fontWeight: 'bold' } },
      data: [
        { value: c.graph_pct, name: '图算法重要性', itemStyle: { color: '#667eea' } },
        { value: c.cf_pct, name: '相似用户经验', itemStyle: { color: '#52c41a' } },
        { value: c.llm_pct, name: '知识点关联分析', itemStyle: { color: '#e67e22' } }
      ]
    }]
  })
  networkCharts.push(chart)
}

// Day 7: AI 问答模块
const showChat = ref(false)
const chatMessages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatRelatedNodes = ref([])
const chatMessagesRef = ref(null)
const suggestedQuestions = [
  '函数和导数有什么关系？',
  '如何理解向量的点积？',
  '三角函数的图像变换有哪些？',
  '排列组合和概率的联系是什么？',
  '空间几何中如何求体积？',
]

let chart = null

const moduleColors = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#48b8d0'
]

const getModuleColor = (module) => {
  const idx = modules.value.indexOf(module)
  return moduleColors[idx % moduleColors.length]
}

const getNodeName = (id) => {
  const node = nodesData.value.find(n => n.id === id)
  return node ? node.name : `节点${id}`
}

// ========== 用户相关 ==========

const USER_KEY = 'math_users'

const loadUsers = () => {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || '[]')
  } catch (e) {
    return []
  }
}

const saveUsers = (users) => {
  localStorage.setItem(USER_KEY, JSON.stringify(users))
}

const handleLogin = () => {
  if (!loginUsername.value || !loginPassword.value) {
    alert('请输入用户名和密码')
    return
  }
  const users = loadUsers()
  const user = users.find(u => u.username === loginUsername.value)
  if (!user || user.password !== loginPassword.value) {
    alert('用户名或密码错误')
    return
  }
  currentUser.value = user.username
  showLoginDialog.value = false
  loginUsername.value = ''
  loginPassword.value = ''
  loadUserProgress()
  updateGraphColors()
  syncWeights()
}

const syncWeights = async () => {
  if (!currentUser.value) return
  try {
    await applyProgressToWeights(currentUser.value, progressData.value)
    await loadEdgeWeights()
    updateChartEdges()
  } catch (e) {
    console.error('Sync weights failed:', e)
  }
}

const handleRegister = () => {
  if (!loginUsername.value || !loginPassword.value) {
    alert('请输入用户名和密码')
    return
  }
  const users = loadUsers()
  if (users.find(u => u.username === loginUsername.value)) {
    alert('用户名已存在')
    return
  }
  users.push({
    username: loginUsername.value,
    password: loginPassword.value,
    progress: {}
  })
  saveUsers(users)
  alert('注册成功，请登录')
  isRegister.value = false
}

const showDeregisterConfirm = ref(false)

const handleLogout = () => {
  currentUser.value = null
  progressData.value = {}
  edgeWeights.value = {}
  updateGraphColors()
}

const handleDeregister = async () => {
  if (!currentUser.value) return
  try {
    await deleteUser(currentUser.value)
  } catch { /* ignore backend error */ }
  // 清除 localStorage 中的用户数据
  const users = loadUsers()
  const idx = users.findIndex(u => u.username === currentUser.value)
  if (idx !== -1) {
    users.splice(idx, 1)
    saveUsers(users)
  }
  currentUser.value = null
  progressData.value = {}
  edgeWeights.value = {}
  updateGraphColors()
  showDeregisterConfirm.value = false
}

// ========== 进度管理 ==========

const loadUserProgress = () => {
  if (!currentUser.value) return
  const users = loadUsers()
  const user = users.find(u => u.username === currentUser.value)
  if (user && user.progress) {
    progressData.value = user.progress
  }
  loadEdgeWeights()
}

const loadEdgeWeights = async () => {
  if (!currentUser.value) {
    edgeWeights.value = {}
    return
  }
  try {
    const res = await getEdgeWeights(currentUser.value)
    const w = {}
    if (res.edges) {
      for (const e of res.edges) {
        w[`${e.from}-${e.to}`] = e.weight
      }
    }
    edgeWeights.value = w
  } catch (e) {
    console.error('Failed to load edge weights:', e)
  }
}

const updateChartEdges = () => {
  if (!chart) return
  const newEdges = edgesData.value.map(edge => ({
    source: edge.from.toString(),
    target: edge.to.toString(),
    lineStyle: {
      curveness: 0.2,
      width: getEdgeWidth(edge.from, edge.to),
      color: getEdgeWeight(edge.from, edge.to) > 1.5 ? '#e67e22' : '#b0b0b0'
    }
  }))
  chart.setOption({ series: [{ links: newEdges }] })
}

const saveUserProgress = () => {
  if (!currentUser.value) return
  const users = loadUsers()
  const idx = users.findIndex(u => u.username === currentUser.value)
  if (idx >= 0) {
    users[idx].progress = progressData.value
    saveUsers(users)
  }
}

const getNodeStatus = (nodeId) => {
  return progressData.value[String(nodeId)] || 'unlearned'
}

const getNodeColor = (nodeId) => {
  const status = getNodeStatus(nodeId)
  if (status === 'mastered') return '#52c41a'
  if (status === 'weak') return '#f5222d'
  return '#ccc'
}

const getStatusText = (status) => {
  if (status === 'mastered') return 'Mastered'
  if (status === 'weak') return 'Weak'
  return 'Unlearned'
}

const getStatusClass = (status) => {
  return `status-${status}`
}

const setNodeStatus = (node, status) => {
  if (!currentUser.value) {
    showLoginDialog.value = true
    return
  }
  progressData.value[String(node.id)] = status
  saveUserProgress()
  updateGraphColors()
  syncWeights()
}

const missingPrerequisites = ref([])

const checkPrerequisites = (nodeId) => {
  if (!nodeDetail.value) {
    missingPrerequisites.value = []
    return []
  }
  const missing = nodeDetail.value.prerequisites.filter(pid => {
    return getNodeStatus(pid) !== 'mastered'
  })
  missingPrerequisites.value = missing
  return missing
}

// ========== 图谱颜色更新 ==========

const updateGraphColors = () => {
  if (!chart) return
  const nodes = nodesData.value.map(node => {
    const status = getNodeStatus(node.id)
    let color = '#ccc' // 未学 = 灰
    if (status === 'mastered') color = '#52c41a' // 已会 = 绿
    if (status === 'weak') color = '#f5222d' // 薄弱 = 红
    return {
      id: node.id.toString(),
      name: node.name,
      value: node.difficulty,
      category: modules.value.indexOf(node.module),
      symbolSize: 40 + node.difficulty * 15,
      itemStyle: { color },
      label: {
        show: true,
        position: 'inside',
        fontSize: 16,
        fontWeight: 'bold',
        color: 'black',
        formatter: '{b}'
      }
    }
  })
  chart.setOption({
    series: [{
      data: nodes
    }]
  })
}

const focusNode = (id) => {
  const node = nodesData.value.find(n => n.id === id)
  if (node) {
    selectNode(node)
  }
}

const selectNode = async (node) => {
  selectedNode.value = node
  if (chart) {
    chart.setOption({
      series: [{
        data: nodesData.value.map(n => ({
          id: n.id.toString(),
          name: n.name,
          value: n.difficulty,
          category: modules.value.indexOf(n.module),
          symbolSize: n.id === node.id ? 80 : 40 + n.difficulty * 15,
          itemStyle: { color: getNodeColor(n.id) },
          label: {
            show: true,
            position: 'inside',
            fontSize: 16,
            fontWeight: 'bold',
            color: 'black',
            formatter: '{b}'
          }
        }))
      }]
    })
  }
  try {
    const data = await getNodeDetail(node.id)
    nodeDetail.value = data
    checkPrerequisites(node.id)
  } catch (error) {
    console.error('Failed to load node detail:', error)
  }
}

const resetLayout = () => {
  if (chart) {
    chart.clear()
    const nodes = nodesData.value.map(node => {
      const status = getNodeStatus(node.id)
      let color = '#ccc'
      if (status === 'mastered') color = '#52c41a'
      if (status === 'weak') color = '#f5222d'
      return {
        id: node.id.toString(),
        name: node.name,
        value: node.difficulty,
        category: modules.value.indexOf(node.module),
        symbolSize: 40 + node.difficulty * 15,
        itemStyle: { color },
        label: {
          show: true,
          position: 'inside',
          fontSize: 16,
          fontWeight: 'bold',
          color: 'black',
          formatter: '{b}'
        }
      }
    })
    const edges = edgesData.value.map(edge => ({
      source: edge.from.toString(),
      target: edge.to.toString(),
      lineStyle: {
        curveness: 0.2,
        width: getEdgeWidth(edge.from, edge.to),
        color: getEdgeWeight(edge.from, edge.to) > 1.5 ? '#e67e22' : '#b0b0b0'
      }
    }))
    const categories = modules.value.map((mod, idx) => ({
      name: mod,
      itemStyle: { color: moduleColors[idx % moduleColors.length] }
    }))
    chart.setOption({
      series: [{
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: edges,
        categories: categories,
        roam: true,
        draggable: true,
        force: {
          repulsion: 800,
          edgeLength: 200,
          gravity: 0.05
        }
      }]
    })
  }
}

const toggleLabels = () => {
  showLabels.value = !showLabels.value
  if (chart) {
    chart.setOption({
      series: [{
        label: { show: showLabels.value }
      }]
    })
  }
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
  setTimeout(() => {
    if (chart) chart.resize()
  }, 300)
}

const toggleAlgorithmPanel = () => {
  showAlgorithms.value = !showAlgorithms.value
  if (showAlgorithms.value) {
    loadAlgorithms()
  }
}

const loadAlgorithms = async () => {
  try {
    const degreeRes = await getDegreeCentrality().catch(e => { console.error('degree err:', e); return {} })
    const betweennessRes = await getBetweennessCentrality().catch(e => { console.error('betweenness err:', e); return {} })
    const pagerankRes = await getPageRank().catch(e => { console.error('pagerank err:', e); return {} })
    const communityRes = await getCommunity().catch(e => { console.error('community err:', e); return {} })
    const compareRes = await getCommunityCompare().catch(e => { console.error('compare err:', e); return {} })
    degreeCentrality.value = degreeRes.centrality || []
    betweennessCentrality.value = betweennessRes.centrality || []
    pagerankCentrality.value = pagerankRes.centrality || []
    pagerankSummary.value = pagerankRes.summary || ''
    communities.value = communityRes.communities || []
    communityCompare.value = compareRes
  } catch (error) {
    console.error('Failed to load algorithms:', error)
  }
}

const loadCommunityExplain = async (nodeId) => {
  communityExplainLoading.value = true
  try {
    const res = await getCommunityExplain(nodeId)
    communityExplain.value = res.error ? null : res
  } catch (e) {
    console.error('explain err:', e)
    communityExplain.value = null
  } finally {
    communityExplainLoading.value = false
  }
}

const findPath = async () => {
  if (!pathStart.value || !pathEnd.value) {
    alert('请输入起始和目标节点ID')
    return
  }
  try {
    const data = await getShortestPath(parseInt(pathStart.value), parseInt(pathEnd.value))
    if (data.error) {
      alert(data.error)
      return
    }
    shortestPath.value = data
    if (chart) {
      const pathNodeIds = data.path.map(p => p.id.toString())
      const nodes = nodesData.value.map(node => {
        const status = getNodeStatus(node.id)
        let color = pathNodeIds.includes(node.id.toString()) ? '#ff0000' : '#ccc'
        if (status === 'mastered') color = pathNodeIds.includes(node.id.toString()) ? '#ff0000' : '#52c41a'
        if (status === 'weak') color = pathNodeIds.includes(node.id.toString()) ? '#ff0000' : '#f5222d'
        return {
          id: node.id.toString(),
          name: node.name,
          value: node.difficulty,
          category: modules.value.indexOf(node.module),
          symbolSize: 40 + node.difficulty * 15,
          itemStyle: { color },
          label: {
            show: true,
            position: 'inside',
            fontSize: 16,
            fontWeight: 'bold',
            color: pathNodeIds.includes(node.id.toString()) ? '#fff' : 'black',
            formatter: '{b}'
          }
        }
      })
      chart.setOption({
        series: [{
          data: nodes
        }]
      })
    }
  } catch (error) {
    console.error('Failed to find path:', error)
  }
}

const findAdaptivePath = async () => {
  if (!pathEnd.value) {
    alert('请输入目标节点ID')
    return
  }
  if (!currentUser.value) {
    alert('请先登录')
    return
  }
  try {
    const data = await getAdaptivePath(currentUser.value, parseInt(pathEnd.value), progressData.value)
    if (data.error) {
      alert(data.error)
      return
    }
    shortestPath.value = data
    if (chart) {
      const pathNodeIds = data.path.map(p => p.id.toString())
      const nodes = nodesData.value.map(node => {
        const status = getNodeStatus(node.id)
        const isInPath = pathNodeIds.includes(node.id.toString())
        let color = isInPath ? '#ff0000' : '#ccc'
        if (status === 'mastered') color = isInPath ? '#ff0000' : '#52c41a'
        if (status === 'weak') color = isInPath ? '#ff0000' : '#f5222d'
        return {
          id: node.id.toString(),
          name: node.name,
          value: node.difficulty,
          category: modules.value.indexOf(node.module),
          symbolSize: 40 + node.difficulty * 15,
          itemStyle: { color },
          label: {
            show: true,
            position: 'inside',
            fontSize: 16,
            fontWeight: 'bold',
            color: isInPath ? '#fff' : 'black',
            formatter: '{b}'
          }
        }
      })
      chart.setOption({ series: [{ data: nodes }] })
    }
  } catch (error) {
    console.error('Failed to find adaptive path:', error)
  }
}

const handleNodeClick = async (params) => {
  if (params.dataType === 'node') {
    const node = nodesData.value.find(n => n.id.toString() === params.data.id)
    if (node) {
      await selectNode(node)
    }
  }
}

const handleResize = () => {
  if (chart) chart.resize()
}

// ========== Day 5: 智能诊断 & 路径推荐 ==========

const runDiagnosis = async () => {
  if (!currentUser.value) {
    showLoginDialog.value = true
    return
  }
  
  diagnosisLoading.value = true
  showDiagnosis.value = true
  try {
    const result = await diagnoseWeakPoints(progressData.value)
    diagnosisResult.value = result
    generateDailySuggestions(result)
    try {
      userModel.value = await getUserModel(currentUser.value, progressData.value)
    } catch (e) {
      console.warn('User model fetch failed:', e)
    }
  } catch (error) {
    console.error('Diagnosis failed:', error)
    alert('诊断失败，请稍后重试')
  } finally {
    diagnosisLoading.value = false
  }
}

const generateDailySuggestions = (diagnosis) => {
  if (!diagnosis) return
  
  const suggestions = []
  
  // 1. 优先建议复习薄弱点
  if (diagnosis.weak_points && diagnosis.weak_points.length > 0) {
    suggestions.push({
      type: 'weak',
      title: '复习薄弱知识点',
      items: diagnosis.weak_points.slice(0, 3).map(wp => ({
        id: wp.id,
        name: wp.name,
        module: wp.module
      }))
    })
  }
  
  // 2. 建议学习缺失的前置知识
  if (diagnosis.missing_prerequisites) {
    const missingItems = []
    for (const [nodeId, data] of Object.entries(diagnosis.missing_prerequisites)) {
      missingItems.push(...data.missing.slice(0, 2))
    }
    if (missingItems.length > 0) {
      suggestions.push({
        type: 'prerequisite',
        title: '补全前置知识',
        items: missingItems.slice(0, 3)
      })
    }
  }
  
  // 3. 建议学习未学的基础知识点（入度为0且未学）
  const unlearnedBasic = nodesData.value.filter(node => {
    const status = getNodeStatus(node.id)
    return status === 'unlearned' && !edgesData.value.some(e => e.to === node.id)
  })
  
  if (unlearnedBasic.length > 0) {
    suggestions.push({
      type: 'new',
      title: '学习新知识点',
      items: unlearnedBasic.slice(0, 3).map(n => ({
        id: n.id,
        name: n.name,
        module: n.module
      }))
    })
  }
  
  dailySuggestions.value = suggestions
  if (suggestions.length > 0) {
    showDailySuggestions.value = true
  }
}

const getLearningPath = async (targetId) => {
  if (!currentUser.value) {
    showLoginDialog.value = true
    return
  }
  if (targetId == null || !nodesData.value.some(n => n.id === targetId)) {
    alert('目标知识点不存在，请刷新页面后重试')
    return
  }
  
  learningPathLoading.value = true
  try {
    const result = await recommendLearningPath(progressData.value, targetId)
    if (result.error) {
      alert(result.error)
      return
    }
    learningPath.value = result
    highlightLearningPath(result.path)
  } catch (error) {
    console.error('Learning path failed:', error)
    alert('获取学习路径失败：' + (error.message || '未知错误'))
  } finally {
    learningPathLoading.value = false
  }
}

const highlightLearningPath = (path) => {
  if (!chart || !path) return
  
  const pathNodeIds = path.map(p => p.id.toString())
  
  const nodes = nodesData.value.map(node => {
    const status = getNodeStatus(node.id)
    const isInPath = pathNodeIds.includes(node.id.toString())
    
    let color = '#ccc'
    if (status === 'mastered') color = '#52c41a'
    if (status === 'weak') color = '#f5222d'
    if (isInPath) color = '#1890ff' // 路径节点用蓝色高亮
    
    const pathIndex = pathNodeIds.indexOf(node.id.toString())
    const opacity = isInPath ? 1 : 0.3
    
    return {
      id: node.id.toString(),
      name: node.name,
      value: node.difficulty,
      category: modules.value.indexOf(node.module),
      symbolSize: isInPath ? 60 : (40 + node.difficulty * 15),
      itemStyle: { 
        color,
        opacity: isInPath ? 1 : 0.4
      },
      label: {
        show: true,
        position: 'inside',
        fontSize: isInPath ? 18 : 16,
        fontWeight: isInPath ? 'bold' : 'normal',
        color: isInPath ? '#fff' : (status === 'mastered' ? '#fff' : 'black')
      }
    }
  })
  
  chart.setOption({
    series: [{
      data: nodes
    }]
  })
}

const clearLearningPath = () => {
  learningPath.value = null
  updateGraphColors()
}

// ========== Day 6: 统计图表 & 热力图 ==========

const computeModuleStats = () => {
  const stats = {}
  modules.value.forEach(mod => {
    stats[mod] = { mastered: 0, weak: 0, unlearned: 0, total: 0 }
  })
  nodesData.value.forEach(node => {
    const status = getNodeStatus(node.id)
    if (!stats[node.module]) {
      stats[node.module] = { mastered: 0, weak: 0, unlearned: 0, total: 0 }
    }
    stats[node.module][status]++
    stats[node.module].total++
  })
  return stats
}

const computeMasteryPercentages = (stats) => {
  const result = {}
  for (const [mod, data] of Object.entries(stats)) {
    result[mod] = data.total > 0 ? Math.round((data.mastered / data.total) * 100) : 0
  }
  return result
}

const getWeakCountPerModule = () => {
  const counts = {}
  nodesData.value.forEach(node => {
    const status = getNodeStatus(node.id)
    if (status === 'weak') {
      counts[node.module] = (counts[node.module] || 0) + 1
    }
  })
  return counts
}

const getHeatmapData = () => {
  const modList = modules.value
  const levels = [1, 2, 3, 4, 5]
  const data = []
  modList.forEach((mod, mi) => {
    levels.forEach((diff, di) => {
      const nodesInCell = nodesData.value.filter(n => n.module === mod && n.difficulty === diff)
      if (nodesInCell.length > 0) {
        const masteredCount = nodesInCell.filter(n => getNodeStatus(n.id) === 'mastered').length
        const ratio = masteredCount / nodesInCell.length
        data.push([mi, di, Math.round(ratio * 100)])
      } else {
        data.push([mi, di, -1])
      }
    })
  })
  return { modules: modList, levels, data }
}

const disposeDashboardCharts = () => {
  dashboardCharts.forEach(c => { if (c) c.dispose() })
  dashboardCharts.length = 0
}

const renderDashboardCharts = () => {
  disposeDashboardCharts()
  
  const stats = computeModuleStats()
  const modList = modules.value
  const levels = [1, 2, 3, 4, 5]

  // 1. 模块掌握程度柱状图
  if (barChartRef.value) {
    const barChart = echarts.init(barChartRef.value)
    dashboardCharts.push(barChart)
    barChart.setOption({
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['已会', '薄弱', '未学'], bottom: 0, textStyle: { fontSize: 12 } },
      grid: { left: '8%', right: '4%', top: '6%', bottom: '22%', containLabel: true },
      xAxis: { type: 'category', data: modList, axisLabel: { rotate: 20, fontSize: 10 } },
      yAxis: { type: 'value', minInterval: 1 },
      series: [
        {
          name: '已会', type: 'bar', stack: 'total',
          itemStyle: { color: '#52c41a' },
          data: modList.map(m => stats[m].mastered)
        },
        {
          name: '薄弱', type: 'bar', stack: 'total',
          itemStyle: { color: '#f5222d' },
          data: modList.map(m => stats[m].weak)
        },
        {
          name: '未学', type: 'bar', stack: 'total',
          itemStyle: { color: '#ccc' },
          data: modList.map(m => stats[m].unlearned)
        }
      ]
    })
  }

  // 2. 模块掌握雷达图
  if (radarChartRef.value) {
    const radarChart = echarts.init(radarChartRef.value)
    dashboardCharts.push(radarChart)
    const percentages = computeMasteryPercentages(stats)
    radarChart.setOption({
      tooltip: {},
      legend: { data: ['掌握程度(%)'], bottom: 0 },
      radar: {
        indicator: modList.map(m => ({ name: m, max: 100 })),
        shape: 'polygon',
        name: { textStyle: { fontSize: 10 } },
        splitArea: { areaStyle: { color: ['rgba(102,126,234,0.02)', 'rgba(102,126,234,0.06)'] } }
      },
      series: [{
        type: 'radar',
        data: [{ value: modList.map(m => percentages[m]), name: '掌握程度(%)', areaStyle: { color: 'rgba(102,126,234,0.3)' }, lineStyle: { color: '#667eea', width: 2 }, itemStyle: { color: '#667eea' } }]
      }]
    })
  }

  // 3. 薄弱知识点分布图
  if (weakChartRef.value) {
    const weakChart = echarts.init(weakChartRef.value)
    dashboardCharts.push(weakChart)
    const weakCounts = getWeakCountPerModule()
    const hasWeak = Object.keys(weakCounts).length > 0
    if (hasWeak) {
      weakChart.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c}个 ({d}%)' },
        series: [{
          type: 'pie',
          radius: ['30%', '65%'],
          center: ['50%', '48%'],
          data: Object.entries(weakCounts).map(([mod, count], idx) => ({
            name: mod, value: count,
            itemStyle: { color: moduleColors[idx % moduleColors.length] }
          })),
          label: { fontSize: 10, formatter: '{b}\n{c}个' },
          emphasis: { label: { fontSize: 14, fontWeight: 'bold' } }
        }]
      })
    } else {
      weakChart.setOption({
        title: { text: '暂无薄弱知识点', left: 'center', top: 'center', textStyle: { fontSize: 14, color: '#999' } }
      })
    }
  }

  // 4. 知识状态热力图
  if (heatmapChartRef.value) {
    const heatmapChart = echarts.init(heatmapChartRef.value)
    dashboardCharts.push(heatmapChart)
    const hmData = getHeatmapData()
    heatmapChart.setOption({
      tooltip: {
        position: 'top',
        formatter: (p) => {
          const mod = hmData.modules[p.value[0]]
          const diff = '★'.repeat(p.value[1] + 1)
          const val = p.value[2] < 0 ? '无数据' : `掌握率: ${p.value[2]}%`
          return `${mod}<br/>难度: ${diff}<br/>${val}`
        }
      },
      grid: { left: '12%', right: '4%', top: '6%', bottom: '12%', containLabel: true },
      xAxis: { type: 'category', data: hmData.modules, axisLabel: { rotate: 20, fontSize: 10 } },
      yAxis: { type: 'category', data: ['★1', '★2', '★3', '★4', '★5'], axisLabel: { fontSize: 11 } },
      visualMap: {
        min: 0, max: 100,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: 0,
        inRange: { color: ['#ccc', '#91cc75', '#52c41a'] },
        text: ['低', '高'],
        textStyle: { fontSize: 10 }
      },
      series: [{
        type: 'heatmap',
        data: hmData.data,
        label: {
          show: true,
          fontSize: 10,
          formatter: (p) => p.value[2] >= 0 ? p.value[2] + '%' : '-'
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
        }
      }]
    })
  }
}

const toggleDashboard = () => {
  showDashboard.value = !showDashboard.value
  if (showDashboard.value) {
    nextTick(() => renderDashboardCharts())
  } else {
    disposeDashboardCharts()
  }
}

const refreshDashboard = () => {
  renderDashboardCharts()
}

// ========== Day 7: AI 问答 ==========

const toggleChat = () => {
  showChat.value = !showChat.value
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  })
}

const renderMessage = (text) => {
  return text.replace(/\n/g, '<br>')
}

const highlightChatRelatedNodes = (nodes) => {
  chatRelatedNodes.value = nodes
  if (!chart || !nodes || nodes.length === 0) return
  const nodeIds = nodes.map(n => n.id.toString())
  const chartNodes = nodesData.value.map(node => {
    const status = getNodeStatus(node.id)
    const isRelated = nodeIds.includes(node.id.toString())
    let color = '#ccc'
    if (status === 'mastered') color = '#52c41a'
    if (status === 'weak') color = '#f5222d'
    if (isRelated) color = '#722ed1'
    return {
      id: node.id.toString(),
      name: node.name,
      value: node.difficulty,
      category: modules.value.indexOf(node.module),
      symbolSize: isRelated ? 65 : (40 + node.difficulty * 15),
      itemStyle: { color, opacity: isRelated ? 1 : 0.35 },
      label: {
        show: true,
        position: 'inside',
        fontSize: isRelated ? 18 : 16,
        fontWeight: isRelated ? 'bold' : 'normal',
        color: isRelated ? '#fff' : 'black'
      }
    }
  })
  chart.setOption({ series: [{ data: chartNodes }] })
}

const handleSendChat = async () => {
  const msg = chatInput.value.trim()
  if (!msg || chatLoading.value) return

  chatMessages.value.push({ role: 'user', content: msg })
  chatInput.value = ''
  chatLoading.value = true
  scrollToBottom()

  const history = chatMessages.value.slice(0, -1).map(m => ({
    role: m.role, content: m.content
  }))

  // 先占位一条空消息，流式逐步填充
  const msgIndex = chatMessages.value.length
  chatMessages.value.push({ role: 'assistant', content: '' })
  scrollToBottom()

  let hasError = false
  await sendChatMessageStream(msg, history, progressData.value, {
    onChunk(token) {
      chatMessages.value[msgIndex].content += token
      scrollToBottom()
    },
    onDone(nodes) {
      chatMessages.value[msgIndex].related_nodes = nodes
      highlightChatRelatedNodes(nodes)
      chatLoading.value = false
      scrollToBottom()
    },
    onError(errMsg) {
      if (!hasError) {
        hasError = true
        chatMessages.value[msgIndex].content = '抱歉：' + errMsg
        chatLoading.value = false
      }
    }
  })
  // 确保 loading 关闭（兜底）
  if (chatLoading.value) chatLoading.value = false
}

const quickQuestion = (q) => {
  chatInput.value = q
  handleSendChat()
}

onMounted(async () => {
  try {
    loading.value = true
    console.log('开始请求数据...')
    const data = await getKnowledgeNetwork()
    console.log('请求成功:', data)
    modules.value = data.modules
    nodesData.value = data.nodes
    edgesData.value = data.edges

    const nodes = data.nodes.map(node => {
      const status = getNodeStatus(node.id)
      let color = '#ccc'
      if (status === 'mastered') color = '#52c41a'
      if (status === 'weak') color = '#f5222d'
      return {
        id: node.id.toString(),
        name: node.name,
        value: node.difficulty,
        category: data.modules.indexOf(node.module),
        symbolSize: 40 + node.difficulty * 15,
        itemStyle: { color },
        label: {
          show: true,
          position: 'inside',
          fontSize: 16,
          fontWeight: 'bold',
          color: 'black',
          formatter: '{b}'
        }
      }
    })

    const edges = data.edges.map(edge => ({
      source: edge.from.toString(),
      target: edge.to.toString(),
      lineStyle: {
        curveness: 0.2,
        width: getEdgeWidth(edge.from, edge.to),
        color: getEdgeWeight(edge.from, edge.to) > 1.5 ? '#e67e22' : '#b0b0b0'
      }
    }))

    const categories = data.modules.map((mod, idx) => ({
      name: mod,
      itemStyle: { color: moduleColors[idx % moduleColors.length] }
    }))

    loading.value = false
    await nextTick()

    chart = echarts.init(chartRef.value)

    const option = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.95)',
        borderColor: '#eee',
        borderWidth: 1,
        textStyle: { color: '#333' },
        formatter: (params) => {
          if (params.dataType === 'node') {
            const prereqCount = edgesData.value.filter(e => e.to === parseInt(params.data.id)).length
            const dependentCount = edgesData.value.filter(e => e.from === parseInt(params.data.id)).length
            const status = getNodeStatus(parseInt(params.data.id))
            const statusText = getStatusText(status)
            return `
              <div style="padding: 4px">
                <b style="font-size: 14px">${params.name}</b><br/>
                <span style="color: ${moduleColors[params.data.category]}">${data.modules[params.data.category]}</span><br/>
                难度: ${'★'.repeat(params.data.value)}${'☆'.repeat(5 - params.data.value)}<br/>
                状态: ${statusText}<br/>
                前置: ${prereqCount} 个 | 后置: ${dependentCount} 个
              </div>
            `
          }
          const fromName = getNodeName(parseInt(params.data.source))
          const toName = getNodeName(parseInt(params.data.target))
          const eWeight = getEdgeWeight(parseInt(params.data.source), parseInt(params.data.target))
          const bar = '█'.repeat(Math.round(eWeight)) + '░'.repeat(Math.max(0, 5 - Math.round(eWeight)))
          return `${fromName} → ${toName}<br/>权重: ${bar} ${eWeight.toFixed(2)}`
        }
      },
      legend: { show: false },
      series: [{
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: edges,
        categories: categories,
        roam: true,
        draggable: true,
        label: {
          show: true,
          position: 'inside',
          fontSize: 16,
          fontWeight: 'bold',
          color: 'black',
          formatter: '{b}'
        },
        force: {
          repulsion: 800,
          edgeLength: 200,
          gravity: 0.05,
          layoutAnimation: true
        },
        lineStyle: {
          color: '#b0b0b0',
          width: 1.5,
          curveness: 0.2
        },
        emphasis: {
          focus: 'self',
          lineStyle: {
            width: 4,
            color: '#667eea'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0,0,0,0.3)'
          }
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 8
      }]
    }

    chart.setOption(option)
    chart.on('click', handleNodeClick)
    window.addEventListener('resize', handleResize)

    // 加载算法结果
    await loadAlgorithms()
  } catch (error) {
    console.error('Failed to load knowledge graph:', error)
    loading.value = false
    errorMsg.value = '无法连接后端，请确认后端已启动在端口 8080'
  }
})

// 算法面板拖拽
const panelPos = ref({ x: null, y: null })
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })
const panelRef = ref(null)

const startDrag = (e) => {
  if (!panelRef.value) return
  const rect = panelRef.value.getBoundingClientRect()
  if (panelPos.value.x === null) {
    panelPos.value.x = rect.left
    panelPos.value.y = rect.top
  }
  dragOffset.value.x = e.clientX - rect.left
  dragOffset.value.y = e.clientY - rect.top
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  e.preventDefault()
}

const onDrag = (e) => {
  if (!isDragging.value) return
  panelPos.value.x = e.clientX - dragOffset.value.x
  panelPos.value.y = e.clientY - dragOffset.value.y
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

// 网络分析面板拖拽
const networkPanelPos = ref({ x: null, y: null })
const networkIsDragging = ref(false)
const networkDragOffset = ref({ x: 0, y: 0 })
const networkPanelRef = ref(null)

const startNetworkDrag = (e) => {
  if (!networkPanelRef.value) return
  const rect = networkPanelRef.value.getBoundingClientRect()
  if (networkPanelPos.value.x === null) {
    networkPanelPos.value.x = rect.left
    networkPanelPos.value.y = rect.top
  }
  networkDragOffset.value.x = e.clientX - rect.left
  networkDragOffset.value.y = e.clientY - rect.top
  networkIsDragging.value = true
  document.addEventListener('mousemove', onNetworkDrag)
  document.addEventListener('mouseup', stopNetworkDrag)
  e.preventDefault()
}

const onNetworkDrag = (e) => {
  if (!networkIsDragging.value) return
  networkPanelPos.value.x = e.clientX - networkDragOffset.value.x
  networkPanelPos.value.y = e.clientY - networkDragOffset.value.y
}

const stopNetworkDrag = () => {
  networkIsDragging.value = false
  document.removeEventListener('mousemove', onNetworkDrag)
  document.removeEventListener('mouseup', stopNetworkDrag)
}

// 混合推荐面板拖拽
const hybridPanelPos = ref({ x: null, y: null })
const hybridIsDragging = ref(false)
const hybridDragOffset = ref({ x: 0, y: 0 })
const hybridPanelRef = ref(null)

const startHybridDrag = (e) => {
  if (!hybridPanelRef.value) return
  const rect = hybridPanelRef.value.getBoundingClientRect()
  if (hybridPanelPos.value.x === null) {
    hybridPanelPos.value.x = rect.left
    hybridPanelPos.value.y = rect.top
  }
  hybridDragOffset.value.x = e.clientX - rect.left
  hybridDragOffset.value.y = e.clientY - rect.top
  hybridIsDragging.value = true
  document.addEventListener('mousemove', onHybridDrag)
  document.addEventListener('mouseup', stopHybridDrag)
  e.preventDefault()
}

const onHybridDrag = (e) => {
  if (!hybridIsDragging.value) return
  hybridPanelPos.value.x = e.clientX - hybridDragOffset.value.x
  hybridPanelPos.value.y = e.clientY - hybridDragOffset.value.y
}

const stopHybridDrag = () => {
  hybridIsDragging.value = false
  document.removeEventListener('mousemove', onHybridDrag)
  document.removeEventListener('mouseup', stopHybridDrag)
}

// 反事实面板拖拽
const cfPanelPos = ref({ x: null, y: null })
const cfIsDragging = ref(false)
const cfDragOffset = ref({ x: 0, y: 0 })
// cfPanelRef already declared

const startCfDrag = (e) => {
  if (!cfPanelRef.value) return
  const rect = cfPanelRef.value.getBoundingClientRect()
  if (cfPanelPos.value.x === null) {
    cfPanelPos.value.x = rect.left
    cfPanelPos.value.y = rect.top
  }
  cfDragOffset.value.x = e.clientX - rect.left
  cfDragOffset.value.y = e.clientY - rect.top
  cfIsDragging.value = true
  document.addEventListener('mousemove', onCfDrag)
  document.addEventListener('mouseup', stopCfDrag)
  e.preventDefault()
}

const onCfDrag = (e) => {
  if (!cfIsDragging.value) return
  cfPanelPos.value.x = e.clientX - cfDragOffset.value.x
  cfPanelPos.value.y = e.clientY - cfDragOffset.value.y
}

const stopCfDrag = () => {
  cfIsDragging.value = false
  document.removeEventListener('mousemove', onCfDrag)
  document.removeEventListener('mouseup', stopCfDrag)
}

onBeforeUnmount(() => {
  stopDrag()
  stopNetworkDrag()
  stopHybridDrag()
  stopCfDrag()
  stopTriplesDrag()
  stopReasoningDrag()
  stopSearchDrag()
  stopExtractionDrag()
  networkCharts.forEach(c => c.dispose())
  if (chart) {
    chart.dispose()
    window.removeEventListener('resize', handleResize)
  }
})
</script>

<style scoped>
.knowledge-graph {
  width: 100%;
  background: white;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
  position: relative;
  height: 960px;
  display: flex;
  flex-direction: column;
}

.user-bar {
  display: flex;
  justify-content: flex-end;
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border-bottom: 1px solid #eee;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-name {
  font-size: 0.9rem;
  color: #333;
  font-weight: 500;
}

.btn-sm {
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.5rem 1rem 0;
}

.graph-header h2 {
  color: #1a1a2e;
  font-size: 1.4rem;
}

.controls {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  color: #555;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.btn.active {
  background: #52c41a;
  color: white;
  border-color: #52c41a;
}

.btn-block {
  width: 100%;
  padding: 0.6rem;
  margin-top: 0.5rem;
}

.btn-danger {
  background: #f5222d;
  color: white;
  border-color: #f5222d;
}

.btn-danger:hover {
  background: #cf1322;
  border-color: #cf1322;
  color: white;
}

.legend {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border-radius: 0;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  color: #666;
  cursor: pointer;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.graph-body {
  display: flex;
  gap: 1rem;
  flex: 1;
  min-height: 0;
  padding: 0 1rem 1rem;
  position: relative;
}

.chart-container {
  flex: 1;
  height: 960px;
  min-height: 700px;
  border-radius: 12px;
  background: #fafafa;
}

.detail-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 500px;
  max-height: 90vh;
  background: #f8f9fa;
  border-radius: 12px;
  padding: 1rem;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  z-index: 999;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #eee;
}

.detail-header h3 {
  color: #1a1a2e;
  font-size: 1.1rem;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #f5222d;
  cursor: pointer;
  line-height: 1;
  padding: 0 0.25rem;
}

.close-btn:hover {
  color: #cf1322;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-row .label {
  color: #888;
  font-size: 0.85rem;
}

.detail-row .value {
  color: #333;
  font-size: 0.9rem;
  font-weight: 500;
}

.status-badge {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-mastered {
  background: #f6ffed;
  color: #52c41a;
}

.status-weak {
  background: #fff1f0;
  color: #f5222d;
}

.status-unlearned {
  background: #fafafa;
  color: #999;
}

.status-actions {
  display: flex;
  gap: 0.5rem;
  margin: 0.5rem 0;
}

.warning-box {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 8px;
  padding: 0.75rem;
  margin: 0.5rem 0;
}

.warning-box p {
  font-size: 0.85rem;
  color: #d48806;
  margin: 0 0 0.5rem 0;
}

.status-mini {
  font-size: 0.7rem;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  margin-left: 0.3rem;
}

.detail-subsection h4 {
  color: #555;
  font-size: 0.9rem;
  margin: 0 0 0.5rem 0;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.tag {
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.tag-prereq {
  background: #e8f0fe;
  color: #1967d2;
}

.tag-prereq:hover {
  background: #1967d2;
  color: white;
}

.tag-weak {
  background: #fff1f0;
  color: #f5222d;
}

.tag-weak:hover {
  background: #f5222d;
  color: white;
}

.tag-dependent {
  background: #fce8e6;
  color: #d93025;
}

.tag-dependent:hover {
  background: #d93025;
  color: white;
}

.empty-text {
  color: #aaa;
  font-size: 0.8rem;
  font-style: italic;
}

.algorithm-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 600px;
  max-height: 90vh;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #eee;
}

.panel-header h3 {
  color: #1a1a2e;
  font-size: 1.1rem;
  margin: 0;
}

/* 反事实推理面板 */
.counterfactual-panel {
  width: 480px;
  right: auto;
  left: 10px;
}

.cf-summary {
  background: #f0f7ff;
  border-left: 3px solid #1677ff;
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  font-size: 0.88rem;
  color: #333;
  line-height: 1.6;
  margin: 0 0 0.8rem 0;
}

.cf-metrics {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.8rem;
}

.cf-metric-card {
  flex: 1;
  background: #fafafa;
  border-radius: 8px;
  padding: 0.6rem;
  text-align: center;
  border: 1px solid #eee;
}

.cf-metric-label {
  font-size: 0.75rem;
  color: #888;
  margin-bottom: 0.3rem;
}

.cf-metric-compare {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  margin-bottom: 0.2rem;
}

.cf-before {
  font-size: 1.1rem;
  font-weight: 600;
  color: #999;
}

.cf-arrow {
  color: #ccc;
  font-size: 0.9rem;
}

.cf-after {
  font-size: 1.1rem;
  font-weight: 700;
  color: #1677ff;
}

.cf-delta {
  font-size: 0.85rem;
  font-weight: 600;
}

.cf-delta.positive { color: #52c41a; }
.cf-delta.zero { color: #999; }

.cf-metric-sub {
  font-size: 0.72rem;
  color: #aaa;
  margin-top: 0.15rem;
}

.cf-section {
  margin-bottom: 0.8rem;
}

.cf-section h4 {
  font-size: 0.9rem;
  color: #333;
  margin: 0 0 0.4rem 0;
}

.cf-path-compare {
  display: flex;
  gap: 0.5rem;
}

.cf-path-col {
  flex: 1;
  background: #f9f9f9;
  border-radius: 6px;
  padding: 0.5rem;
}

.cf-path-label {
  font-size: 0.78rem;
  color: #888;
  margin-bottom: 0.3rem;
}

.cf-path-nodes {
  font-size: 0.82rem;
  line-height: 1.5;
  word-break: break-all;
}

.cf-path-nodes .current {
  color: #1677ff;
  font-weight: 600;
}

.path-connector { color: #ccc; font-size: 0.75rem; }

.cf-path-length {
  font-size: 0.78rem;
  color: #666;
  margin-top: 0.2rem;
}

.cf-module-list {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.cf-module-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.82rem;
}

.cf-module-name {
  width: 90px;
  flex-shrink: 0;
  color: #555;
}

.cf-module-bar-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.cf-module-bar-bg {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.cf-module-bar-before {
  height: 100%;
  background: #91caff;
  border-radius: 4px;
  transition: width 0.3s;
}

.cf-module-pct {
  font-size: 0.78rem;
  color: #666;
  white-space: nowrap;
}

.counterfactual-section {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #eee;
}

.btn-cf {
  background: #f0f5ff;
  border: 1px solid #91caff;
  color: #1677ff;
}

.btn-cf:hover {
  background: #e6f0ff;
  border-color: #1677ff;
}

.cf-select {
  padding: 0.25rem 0.4rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #555;
  background: white;
}

/* 三元组面板 */
.triples-panel {
  width: 640px;
  right: auto;
  left: 10px;
}

.triples-filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  color: #555;
}

.triples-count {
  font-size: 0.78rem;
  color: #999;
  margin-left: auto;
}

.loading-hint {
  text-align: center;
  color: #999;
  padding: 2rem;
  font-size: 0.85rem;
}

.triples-table-wrapper {
  max-height: 50vh;
  overflow-y: auto;
}

.triples-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.triples-table th {
  background: #fafafa;
  padding: 0.4rem 0.6rem;
  text-align: left;
  font-weight: 500;
  color: #555;
  border-bottom: 2px solid #eee;
  position: sticky;
  top: 0;
  z-index: 1;
}

.triples-table td {
  padding: 0.35rem 0.6rem;
  border-bottom: 1px solid #f5f5f5;
}

.triples-table tr:hover td {
  background: #f8f9ff;
}

.triple-entity {
  color: #1677ff;
  cursor: default;
}

.triple-entity.is-node {
  cursor: pointer;
  text-decoration: underline dotted;
}

.triple-entity.is-node:hover {
  color: #0958d9;
}

.triple-rel {
  display: inline-block;
  background: #f0f5ff;
  color: #1677ff;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-size: 0.78rem;
}

/* 语义推理面板 */
.reasoning-panel {
  width: 520px;
  right: auto;
  left: 10px;
}

.reasoning-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
  color: #555;
}

.reasoning-controls label {
  white-space: nowrap;
}

.reasoning-params {
  margin: 0.5rem 0;
}

.reasoning-param-row {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-bottom: 0.3rem;
  font-size: 0.85rem;
  color: #555;
}

.reasoning-param-row .input-field {
  width: 80px;
}

.reasoning-hint {
  font-size: 0.85rem;
  color: #666;
  margin: 0.3rem 0;
}

.reasoning-result {
  margin-top: 0.5rem;
}

.reasoning-explanation {
  background: #f0f7ff;
  border-left: 3px solid #1677ff;
  padding: 0.5rem 0.7rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.reasoning-explanation h4 {
  font-size: 0.85rem;
  margin: 0 0 0.3rem 0;
  color: #1677ff;
}

.reasoning-explanation p {
  font-size: 0.85rem;
  color: #333;
  line-height: 1.5;
  margin: 0;
}

.reasoning-rule-name {
  margin-bottom: 0.5rem;
}

.tag-reasoning {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #52c41a;
}

.reasoning-detail {
  margin-top: 0.5rem;
}

.reasoning-detail h4 {
  font-size: 0.85rem;
  color: #333;
  margin: 0 0 0.3rem 0;
}

.impact-list {
  max-height: 200px;
  overflow-y: auto;
}

.impact-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.4rem;
  border-bottom: 1px solid #f5f5f5;
  font-size: 0.82rem;
}

.impact-item.impact-ready {
  background: #f6ffed;
}

.impact-name {
  color: #1677ff;
  cursor: pointer;
  flex: 1;
}

.impact-name:hover {
  color: #0958d9;
}

.impact-info {
  color: #888;
  font-size: 0.78rem;
}

.impact-badge {
  font-size: 0.75rem;
  color: #52c41a;
}

.path-item {
  display: flex;
  align-items: flex-start;
  gap: 0.3rem;
  padding: 0.3rem 0.4rem;
  border-bottom: 1px solid #f5f5f5;
  font-size: 0.82rem;
}

.path-rank {
  font-weight: 600;
  color: #888;
  min-width: 2em;
}

.path-nodes {
  flex: 1;
  line-height: 1.6;
}

.path-node-name {
  color: #1677ff;
  cursor: pointer;
}

.path-node-name:hover {
  color: #0958d9;
}

.path-current {
  font-weight: 600;
  color: #f5222d !important;
}

.path-len {
  color: #888;
  font-size: 0.78rem;
  white-space: nowrap;
}

.chain-item {
  background: #fafafa;
  border-radius: 6px;
  padding: 0.4rem 0.5rem;
  margin-bottom: 0.4rem;
}

.chain-type {
  font-size: 0.78rem;
  color: #1677ff;
  font-weight: 500;
  margin-bottom: 0.2rem;
}

.chain-nodes {
  font-size: 0.82rem;
  line-height: 1.5;
  margin-bottom: 0.2rem;
}

.chain-explain {
  font-size: 0.78rem;
  color: #666;
  line-height: 1.4;
}

.error-text {
  color: #f5222d;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

/* 语义检索面板 */
.search-panel {
  width: 480px;
  right: auto;
  left: 10px;
}

.search-filters {
  margin-bottom: 0.5rem;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin-bottom: 0.3rem;
  font-size: 0.85rem;
  color: #555;
}

.search-row label {
  white-space: nowrap;
  min-width: 5em;
}

.search-row .input-field {
  flex: 1;
}

.search-count {
  font-size: 0.82rem;
  color: #888;
  margin: 0.3rem 0;
}

.search-result-list {
  max-height: 300px;
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.15s;
}

.search-result-item:hover {
  background: #f0f5ff;
}

.search-result-name {
  flex: 1;
  color: #1677ff;
  font-size: 0.85rem;
}

.search-result-module {
  font-size: 0.72rem;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  white-space: nowrap;
}

.search-result-diff {
  font-size: 0.75rem;
  color: #faad14;
}

/* 实体抽取面板 */
.extraction-panel {
  width: 520px;
  right: auto;
  left: 10px;
}

.extraction-summary {
  margin-bottom: 0.5rem;
}

.extraction-summary h4 {
  font-size: 0.85rem;
  margin: 0 0 0.3rem 0;
  color: #333;
}

.extraction-metrics {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.extraction-metrics .cf-metric-card {
  padding: 0.4rem 0.3rem;
}

.extraction-metrics .cf-metric-label {
  font-size: 0.7rem;
}

.extraction-metrics .cf-after {
  font-size: 1rem;
  font-weight: 700;
  color: #1677ff;
}

.extraction-metrics .cf-detail {
  font-size: 1rem;
  font-weight: 700;
}
.extraction-metrics .cf-detail.positive { color: #52c41a; }
.extraction-metrics .cf-detail.zero { color: #f5222d; }

.extraction-section {
  margin-bottom: 0.5rem;
}

.extraction-section h4 {
  font-size: 0.85rem;
  color: #333;
  margin: 0 0 0.3rem 0;
}

.ext-module-list {
  max-height: 200px;
  overflow-y: auto;
}

.ext-module-row, .ext-diff-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.2rem;
  font-size: 0.8rem;
}

.ext-mod-name {
  width: 110px;
  flex-shrink: 0;
  color: #555;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ext-mod-bar-bg {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.ext-mod-bar {
  display: block;
  height: 100%;
  background: #91caff;
  border-radius: 4px;
  transition: width 0.3s;
}

.ext-mod-bar.diff-bar { background: #b7eb8f; }

.ext-mod-cnt {
  width: 30px;
  text-align: right;
  color: #888;
  font-size: 0.78rem;
}

.ext-diff-label {
  width: 80px;
  flex-shrink: 0;
  color: #faad14;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.panel-body {
  padding: 0;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.algorithm-section {
  background: white;
  border-radius: 8px;
  padding: 0.75rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.algorithm-section h4 {
  color: #333;
  font-size: 0.95rem;
  margin: 0 0 0.5rem 0;
}

.centrality-list {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.centrality-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.centrality-item:hover {
  background: #e8f0fe;
}

.centrality-rank {
  font-size: 0.8rem;
  color: #667eea;
  font-weight: bold;
  min-width: 60px;
}

.centrality-name {
  flex: 1;
  font-size: 0.85rem;
  color: #333;
}

.centrality-module {
  font-size: 0.75rem;
  font-weight: 500;
}

.centrality-score {
  font-size: 0.7rem;
  color: #e67e22;
  margin-left: auto;
  font-family: monospace;
}

.btn-adaptive {
  background: #e67e22;
  color: white;
  border-color: #e67e22;
  font-size: 0.75rem;
  padding: 0.4rem 0.6rem;
}

.btn-adaptive:hover {
  background: #d35400;
  border-color: #d35400;
}

.stats-table { width:100%; border-collapse:collapse; font-size:0.8rem; }
.stats-table td { padding:2px 6px; border:1px solid #eee; }
.stats-table td:nth-child(odd) { color:#888; white-space:nowrap; }
.stats-table td:nth-child(even) { font-weight:bold; text-align:right; }

.compare-table { width:100%; border-collapse:collapse; font-size:0.8rem; margin-top:0.3rem; }
.compare-table th, .compare-table td { padding:3px 8px; border:1px solid #eee; text-align:center; }
.compare-table th { background:#f5f5f5; color:#888; font-weight:normal; }
.compare-table td:first-child { color:#888; text-align:left; }
.compare-table td:not(:first-child) { font-weight:bold; }

.fit-table { width:100%; border-collapse:collapse; font-size:0.78rem; margin:0.4rem 0; }
.fit-table th, .fit-table td { padding:2px 8px; border:1px solid #eee; text-align:center; }
.fit-table th { background:#f5f5f5; color:#888; font-weight:normal; }
.fit-table td:first-child { color:#888; text-align:left; }

.weight-legend {
  margin-top: 0.5rem;
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
  font-size: 0.75rem;
  color: #888;
}

.pagerank-summary {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: #fff7e6;
  border-radius: 6px;
  font-size: 0.8rem;
  color: #8a6d3b;
  line-height: 1.5;
  border-left: 3px solid #e67e22;
}

.community-item {
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
}

.community-header {
  font-size: 0.85rem;
  color: #555;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.community-nodes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.path-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.input-field {
  flex: 1;
  padding: 0.4rem 0.6rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.85rem;
}

.path-result {
  background: #f0f7ff;
  border-radius: 6px;
  padding: 0.5rem;
}

.path-result p {
  font-size: 0.85rem;
  color: #333;
  margin: 0 0 0.5rem 0;
}

.path-nodes {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.85rem;
}

.path-node {
  color: #1967d2;
  font-weight: 500;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 400px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  color: #1a1a2e;
  font-size: 1.2rem;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  color: #555;
  margin-bottom: 0.3rem;
}

.form-switch {
  text-align: center;
  font-size: 0.85rem;
  color: #666;
  margin-top: 1rem;
}

.form-switch a {
  color: #667eea;
  text-decoration: none;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 16px;
  z-index: 10;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-overlay p {
  margin-top: 0.75rem;
  color: #666;
}

@media (max-width: 1200px) {
  .graph-body {
    flex-direction: column;
  }
  .detail-panel, .algorithm-panel, .counterfactual-panel, .triples-panel, .reasoning-panel, .search-panel, .extraction-panel {
    width: 100%;
  }
  .chart-container {
    height: 400px;
  }
}

.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  justify-content: center;
  align-items: center;
  border-radius: 16px;
  z-index: 10;
}

.error-overlay p {
  color: #e53e3e;
  font-size: 1rem;
  text-align: center;
  padding: 1rem;
}

/* Day 5: 智能诊断 & 路径推荐样式 */
.btn-diagnosis {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.btn-diagnosis:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.btn-suggestion {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
  border: none;
}

.btn-suggestion:hover {
  opacity: 0.9;
}

.diagnosis-panel, .suggestion-panel, .learning-path-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 350px;
  max-height: calc(100% - 20px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  z-index: 100;
  overflow-y: auto;
}

.network-analysis-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 520px;
  max-height: calc(100vh - 20px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.network-analysis-panel .panel-content {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.network-analysis-panel .analysis-section {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
}

.network-analysis-panel .analysis-section h4 {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
  color: #333;
}

.network-analysis-panel .analysis-summary {
  font-size: 0.8rem;
  color: #666;
  margin: 0.5rem 0 0;
  line-height: 1.5;
}

.network-analysis-panel .hub-list,
.network-analysis-panel .seed-list {
  margin: 0.5rem 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  align-items: center;
}

.network-analysis-panel .hub-label {
  font-size: 0.8rem;
  color: #888;
  margin-right: 0.3rem;
}

.tag-seed {
  background: #667eea !important;
  color: white !important;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #eee;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #f5222d;
  cursor: pointer;
  line-height: 1;
  padding: 0 0.25rem;
  opacity: 1;
}

.close-btn:hover {
  color: #cf1322;
}

.panel-header h3 {
  margin: 0;
  font-size: 1rem;
}

.diagnosis-summary {
  display: flex;
  justify-content: space-around;
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.summary-item {
  text-align: center;
}

.summary-number {
  display: block;
  font-size: 1.5rem;
  font-weight: bold;
  color: #667eea;
}

.summary-label {
  font-size: 0.8rem;
  color: #666;
}

.diagnosis-section {
  margin-bottom: 1rem;
}

.diagnosis-section h4 {
  color: #555;
  font-size: 0.9rem;
  margin: 0 0 0.5rem 0;
}

.weak-list, .missing-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.weak-item, .tag-missing {
  padding: 0.5rem;
  background: #fff1f0;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
}

.weak-item:hover, .tag-missing:hover {
  background: #f5222d;
  color: white;
}

.weak-name, .missing-title {
  font-size: 0.85rem;
}

.weak-module, .suggestion-module {
  font-size: 0.75rem;
}

.missing-section {
  margin-bottom: 0.8rem;
}

.missing-title {
  margin: 0 0 0.3rem 0;
  color: #666;
}

.diagnosis-actions {
  margin-top: 1rem;
}

.overall-pct {
  float: right;
  font-size: 0.78rem;
  color: #888;
  font-weight: normal;
}

.module-mastery-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.module-mastery-item {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.module-mastery-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.module-name {
  flex: 1;
  color: #333;
}

.module-count {
  color: #999;
  font-size: 0.75rem;
}

.module-status-tag {
  font-size: 0.7rem;
  font-weight: bold;
  padding: 1px 6px;
  border-radius: 8px;
  color: white;
}

.module-status-tag.status-strong { background: #52c41a; }
.module-status-tag.status-moderate { background: #faad14; }
.module-status-tag.status-weak { background: #f5222d; }

.mastery-bar-bg {
  height: 8px;
  background: #eee;
  border-radius: 4px;
  overflow: hidden;
}

.mastery-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s;
}

.suggestion-group {
  margin-bottom: 1rem;
}

.suggestion-group h4 {
  color: #555;
  font-size: 0.9rem;
  margin: 0 0 0.5rem 0;
}

.suggestion-items {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.suggestion-item {
  padding: 0.5rem;
  background: #f0f5ff;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
}

.suggestion-item:hover {
  background: #667eea;
  color: white;
}

.suggestion-name {
  font-size: 0.85rem;
  flex: 1;
}

.path-stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 0.8rem;
  background: #f0f5ff;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #555;
}

.path-sequence {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  align-items: center;
}

.path-step {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

.step-mastered {
  background: #f6ffed;
  color: #52c41a;
}

.step-weak {
  background: #fff1f0;
  color: #f5222d;
}

.step-unlearned {
  background: #fafafa;
  color: #999;
}

.step-number {
  font-weight: bold;
}

.step-arrow {
  color: #ccc;
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Day 6: 仪表盘样式 */
.btn-dashboard {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
  border: none;
}
.btn-dashboard:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.dashboard-section {
  background: #f5f7fa;
  border-radius: 16px;
  padding: 1.5rem;
  margin-top: 1rem;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.dashboard-header h2 {
  font-size: 1.4rem;
  color: #333;
}

.dashboard-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.dashboard-user {
  font-size: 0.85rem;
  color: #666;
  margin-left: 0.5rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.2rem;
}

.dashboard-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  overflow: hidden;
  transition: all 0.3s;
}

.dashboard-card:hover {
  box-shadow: 0 6px 24px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.card-header {
  padding: 0.8rem 1rem;
  border-bottom: 1px solid #f0f0f0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.card-header h3 {
  margin: 0;
  font-size: 0.95rem;
}

.chart-box {
  width: 100%;
  height: 280px;
  padding: 0.5rem;
}

/* Day 7: AI 问答样式 */
.btn-chat {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}
.btn-chat:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.chat-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 420px;
  max-height: calc(100% - 20px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  z-index: 200;
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px 12px 0 0;
}

.chat-header h3 {
  margin: 0;
  font-size: 1rem;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  min-height: 300px;
  max-height: 400px;
}

.chat-welcome {
  text-align: center;
  padding: 1.5rem 1rem;
  color: #666;
}

.chat-welcome p {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.chat-suggestions {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 1rem;
}

.suggestion-btn {
  padding: 0.5rem 0.8rem;
  background: #f0f5ff;
  border: 1px solid #d6e4ff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  color: #1967d2;
  transition: all 0.2s;
}

.suggestion-btn:hover {
  background: #1967d2;
  color: white;
  border-color: #1967d2;
}

.chat-message {
  display: flex;
  gap: 0.6rem;
  margin-bottom: 1rem;
}

.msg-avatar {
  font-size: 1.3rem;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  border-radius: 50%;
}

.msg-content {
  flex: 1;
  background: #f8f9fa;
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  font-size: 0.88rem;
  line-height: 1.5;
}

.chat-message.user .msg-content {
  background: #e8f0fe;
}

.msg-text {
  color: #333;
  word-break: break-word;
}

.msg-thinking {
  color: #999;
  font-style: italic;
}

.msg-nodes {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid #eee;
}

.msg-nodes .tag {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  color: white;
  cursor: pointer;
}

.chat-input-area {
  display: flex;
  gap: 0.5rem;
  padding: 0.8rem 1rem;
  border-top: 1px solid #eee;
}

.chat-input {
  flex: 1;
  padding: 0.6rem 0.8rem;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102,126,234,0.2);
}

.btn-send {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.btn-send:hover {
  opacity: 0.9;
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-related {
  padding: 0.6rem 1rem;
  border-top: 1px solid #f0f0f0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
  background: #fafafa;
  border-radius: 0 0 12px 12px;
}

.related-label {
  font-size: 0.8rem;
  color: #666;
  font-weight: 500;
}

.chat-related .tag {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  color: white;
  cursor: pointer;
}

/* 混合推荐面板 */
.hybrid-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 480px;
  max-height: calc(100vh - 20px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.hybrid-panel .panel-content {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.hybrid-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.hybrid-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 8px;
  background: #f8f9fa;
  cursor: pointer;
  transition: background 0.15s;
}

.hybrid-item:hover {
  background: #e8f0fe;
}

.hybrid-rank {
  font-size: 0.85rem;
  font-weight: bold;
  color: #667eea;
  min-width: 24px;
}

.hybrid-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.hybrid-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #333;
}

.hybrid-module {
  font-size: 0.7rem;
  font-weight: 500;
}

.hybrid-status {
  font-size: 0.65rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}

.hybrid-scores {
  display: flex;
  gap: 0.2rem;
  align-items: center;
  min-width: 60px;
}

.score-bar {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: #eee;
  display: inline-flex;
  align-items: flex-end;
  overflow: hidden;
}

.score-fill {
  width: 100%;
  border-radius: 0 0 4px 4px;
  transition: height 0.3s;
}

.score-graph { background: #667eea; }
.score-cf { background: #52c41a; }
.score-llm { background: #e67e22; }
</style>
