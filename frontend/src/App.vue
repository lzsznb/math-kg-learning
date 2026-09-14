<template>
  <div id="app">
    <nav class="navbar">
      <h1>高中数学智能学习助手</h1>
    </nav>
    <main class="container">
      <KnowledgeGraph />
    </main>
  </div>
</template>

<script setup>
import KnowledgeGraph from './components/KnowledgeGraph.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f5f7fa;
}

.navbar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem 2rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.navbar h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.container {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 0.5rem;
  flex: 1;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

body {
  min-height: 100vh;
}
</style>
