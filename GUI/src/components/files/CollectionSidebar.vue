<script setup lang="ts">
import { FolderIcon, PlusIcon } from 'lucide-vue-next';

defineProps<{
  collections: string[];
  selectedCollection: string;
}>();

const emit = defineEmits<{
  (e: 'select', collection: string): void;
  (e: 'create'): void;
}>();
</script>

<template>
  <aside class="w-64 bg-white border-r border-gray-200 flex flex-col">
    <div class="p-4 border-b border-gray-200 font-bold text-lg text-indigo-600 flex justify-between items-center">
      <span>Katalogi plików</span>
      <button @click="emit('create')" class="text-gray-400 hover:text-indigo-600 transition-colors" title="Nowy katalog">
        <PlusIcon class="w-5 h-5" />
      </button>
    </div>
    
    <div class="flex-1 overflow-y-auto p-2">
      <ul class="space-y-1">
        <li v-for="collection in collections" :key="collection">
          <button 
            @click="emit('select', collection)"
            :class="[
              'w-full flex items-center px-3 py-2 rounded-md text-sm transition-colors',
              selectedCollection === collection ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-600 hover:bg-gray-100'
            ]"
          >
            <FolderIcon class="w-4 h-4 mr-2" />
            {{ collection }}
          </button>
        </li>
        
        <li v-if="!collections.includes(selectedCollection)">
          <button class="w-full flex items-center px-3 py-2 rounded-md text-sm bg-indigo-50 text-indigo-700 font-medium">
            <FolderIcon class="w-4 h-4 mr-2" />
            {{ selectedCollection }} (Nowy)
          </button>
        </li>
      </ul>
    </div>
  </aside>
</template>