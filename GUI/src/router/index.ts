import { createRouter, createWebHistory } from 'vue-router';
import FileManagerView from '../views/FileManagerView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { 
      path: '/', 
      redirect: '/files' 
    },
    { 
      path: '/files', 
      name: 'Files', 
      component: FileManagerView 
    },
    // Tutaj w przyszłości dodamy:
    // { path: '/suites', name: 'TestSuites', component: () => import('../views/TestSuitesView.vue') }
    // { path: '/cases', name: 'TestCases', component: () => import('../views/TestCasesView.vue') }
  ]
});

export default router;