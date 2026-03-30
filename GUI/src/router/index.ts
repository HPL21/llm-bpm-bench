import { createRouter, createWebHistory } from 'vue-router';
import FileManagerView from '../views/FileManagerView.vue';
import TestSuitesView from '../views/TestSuitesView.vue';

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
    { 
      path: '/suites',
      name: 'TestSuites',
      component: TestSuitesView
    },
  ]
});

export default router;