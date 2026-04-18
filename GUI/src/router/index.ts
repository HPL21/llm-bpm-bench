import { createRouter, createWebHistory } from 'vue-router';
import FileManagerView from '../views/FileManagerView.vue';
import TestSuitesView from '../views/TestSuitesView.vue';
import TestCasesView from '../views/TestCasesView.vue';
import ModelsView from '../views/ModelsView.vue';
import BenchmarksView from '../views/BenchmarksView.vue';
import BenchmarkDetailView from '../views/BenchmarkDetailView.vue';

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
    {
      path: '/suites/:id/cases',
      name: 'TestCases',
      component: TestCasesView,
      props: true
    },
    {
      path: '/models',
      name: 'Models',
      component: ModelsView
    },
    {
      path: '/benchmarks',
      name: 'Benchmarks',
      component: BenchmarksView
    },
    {
      path: '/benchmarks/:id',
      name: 'BenchmarkDetail',
      component: BenchmarkDetailView,
      props: true
    }
  ]
});

export default router;