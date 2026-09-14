const apiBase = 'http://localhost:8080/api'

export const getKnowledgeNetwork = () => fetch(apiBase + '/knowledge').then(res => res.json())
export const getNodes = () => fetch(apiBase + '/nodes').then(res => res.json())
export const getEdges = () => fetch(apiBase + '/edges').then(res => res.json())
export const getModules = () => fetch(apiBase + '/modules').then(res => res.json())
export const getNodeDetail = (nodeId) => fetch(apiBase + `/node/${nodeId}`).then(res => res.json())
export const getDegreeCentrality = () => fetch(apiBase + '/centrality/degree').then(res => res.json())
export const getBetweennessCentrality = () => fetch(apiBase + '/centrality/betweenness').then(res => res.json())
export const getPageRank = () => fetch(apiBase + '/centrality/pagerank').then(res => res.json())
export const getCommunity = () => fetch(apiBase + '/community').then(res => res.json())
export const getCommunityCompare = () => fetch(apiBase + '/community/compare').then(res => res.json())
export const getCommunityExplain = (nodeId) => fetch(apiBase + `/community/explain/${nodeId}`).then(res => res.json())
export const getShortestPath = (startId, endId) => fetch(apiBase + `/shortest-path/${startId}/${endId}`).then(res => res.json())

export const diagnoseWeakPoints = (progress) =>
  fetch(apiBase + '/diagnosis/weak-points', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(progress)
  }).then(res => res.json())

export const recommendLearningPath = (progress, targetId) =>
  fetch(apiBase + `/recommendation/learning-path?target_id=${targetId}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(progress)
  }).then(res => res.json())

// 非流式聊天（兼容旧调用）
export const sendChatMessage = (message, history, progress) =>
  fetch(apiBase + '/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, progress })
  }).then(res => res.json())

// 动态加权边
export const getEdgeWeights = (userId) => fetch(apiBase + `/edge/weights/${userId}`).then(res => res.json())
export const updateEdgeWeight = (userId, fromNode, toNode, delta) =>
  fetch(apiBase + '/edge/weight', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, from: fromNode, to: toNode, delta })
  }).then(res => res.json())
export const applyProgressToWeights = (userId, progress) =>
  fetch(apiBase + '/edge/weights/apply-progress', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, progress })
  }).then(res => res.json())
export const getAdaptivePath = (userId, targetId, progress) =>
  fetch(apiBase + `/adaptive-path/${userId}/${targetId}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ progress })
  }).then(res => res.json())

export const getUserModel = (userId, progress) =>
  fetch(apiBase + `/user-model/${userId}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ progress })
  }).then(res => res.json())

export const deleteUser = (userId) =>
  fetch(apiBase + `/user/${userId}`, { method: 'DELETE' }).then(res => res.json())

export const getNetworkAnalysis = () =>
  fetch(apiBase + '/network-analysis').then(res => res.json())

export const getCounterfactual = (userId, progress, nodeId, newStatus = "mastered") =>
  fetch(apiBase + '/counterfactual', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, progress, node_id: nodeId, new_status: newStatus })
  }).then(res => res.json())

export const getKGTriples = (relation = null) =>
  fetch(apiBase + '/kg/triples' + (relation ? '?relation=' + encodeURIComponent(relation) : '')).then(res => res.json())

export const getTransitiveClosure = (nodeId) =>
  fetch(apiBase + '/kg/reasoning/transitive-closure', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ node_id: nodeId })
  }).then(res => res.json())

export const getRuleReasoning = (rule, params) =>
  fetch(apiBase + '/kg/reasoning/rules', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rule, params })
  }).then(res => res.json())

export const getKGQuery = (query) =>
  fetch(apiBase + '/kg/query', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(query)
  }).then(res => res.json())

export const runEntityExtraction = () =>
  fetch(apiBase + '/kg/extract-entities', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  }).then(res => res.json())

export const getEntityStatistics = () =>
  fetch(apiBase + '/kg/entity-statistics').then(res => res.json())

export const getHybridRecommend = (userId, progress, allUsersProgress) =>
  fetch(apiBase + '/recommend/hybrid', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, progress, all_users_progress: allUsersProgress })
  }).then(res => res.json())

// 流式聊天：回调 onChunk(token) / onDone(relatedNodes) / onError(msg)
export const sendChatMessageStream = async (message, history, progress, { onChunk, onDone, onError }) => {
  try {
    const res = await fetch(apiBase + '/chat/stream', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history, progress })
    })
    if (!res.ok) { onError?.('网络错误'); return }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let reading = true
    while (reading) {
      const { done, value } = await reader.read()
      reading = !done
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') return
          try {
            const data = JSON.parse(payload)
            if (data.type === 'chunk') onChunk?.(data.content)
            else if (data.type === 'done') onDone?.(data.related_nodes || [])
            else if (data.type === 'error') onError?.(data.content)
          } catch { /* ignore parse errors */ }
        }
      }
    }
  } catch (e) {
    onError?.(e.message)
  }
}
