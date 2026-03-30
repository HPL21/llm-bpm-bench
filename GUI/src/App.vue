<script setup lang="ts">
import { DatabaseIcon, FolderOpenIcon } from 'lucide-vue-next';
</script>

<template>
  <div class="flex flex-col h-screen font-sans bg-gray-100">
    <header class="bg-slate-900 text-white shadow-md z-20">
      <div class="flex items-center px-6 py-3">
        <div class="text-lg font-bold mr-8 tracking-wide flex items-center">
          <span class="text-indigo-400 mr-2">LLM</span> <span class="text-white-400 mr-2">BPM</span> <span
            class="text-indigo-400 mr-2">Bench</span>
        </div>

        <nav class="flex space-x-1">
          <router-link to="/files" class="px-4 py-2 rounded-md text-sm font-medium flex items-center transition-colors"
            active-class="bg-slate-800 text-indigo-400"
            inactive-class="text-gray-300 hover:bg-slate-800 hover:text-white">
            <FolderOpenIcon class="w-4 h-4 mr-2" />
            Magazyn Plików
          </router-link>

          <router-link to="/suites" class="px-4 py-2 rounded-md text-sm font-medium flex items-center transition-colors"
            active-class="bg-slate-800 text-indigo-400"
            inactive-class="text-gray-300 hover:bg-slate-800 hover:text-white">
            <DatabaseIcon class="w-4 h-4 mr-2" />
            Zbiory Testowe
          </router-link>

        </nav>
      </div>
    </header>

    <div class="flex-1 overflow-hidden relative">
      <router-view />
    </div>
  </div>
</template>

<style>
</style>