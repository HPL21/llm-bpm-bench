<script setup lang="ts">
import { FolderIcon, FileIcon, Trash2Icon } from 'lucide-vue-next';
import type { FileAsset } from '../../services/api';

defineProps<{
  files: FileAsset[];
}>();

const emit = defineEmits<{
  (e: 'delete', id: string): void;
}>();
</script>

<template>
  <div class="flex-1 overflow-y-auto p-6 bg-gray-50">
    <div v-if="files.length === 0" class="text-center py-12 text-gray-400">
      <FolderIcon class="w-16 h-16 mx-auto mb-4 opacity-20" />
      <p class="text-lg">Brak plików w tym katalogu.</p>
      <p class="text-sm mt-1">Kliknij "Wgraj pliki" aby dodać nowe dokumenty.</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      <div 
        v-for="file in files" 
        :key="file.id"
        class="bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex flex-col hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="bg-indigo-100 p-2 rounded text-indigo-600">
            <FileIcon class="w-6 h-6" />
          </div>
          <button 
            @click="emit('delete', file.id)"
            class="text-gray-400 hover:text-red-500 transition-colors"
            title="Usuń plik"
          >
            <Trash2Icon class="w-4 h-4" />
          </button>
        </div>
        
        <h3 class="font-medium text-sm text-gray-800 truncate mb-1" :title="file.filename">
          {{ file.filename }}
        </h3>
        <p class="text-xs text-gray-500 truncate">
          {{ file.content_type }}
        </p>
      </div>
    </div>
  </div>
</template>