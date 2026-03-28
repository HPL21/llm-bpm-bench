<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { FileService, type FileAsset } from '../services/api';
import { FolderIcon, UploadCloudIcon } from 'lucide-vue-next';

import CollectionSidebar from '../components/files/CollectionSidebar.vue';
import FileGrid from '../components/files/FileGrid.vue';

const files = ref<FileAsset[]>([]);
const selectedCollection = ref<string>('default');
const isUploading = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);

const collections = computed(() => Array.from(new Set(files.value.map(f => f.collection_name))));
const currentFiles = computed(() => files.value.filter(f => f.collection_name === selectedCollection.value));

const loadFiles = async () => {
  try {
    files.value = await FileService.getAllFiles();
    if (!collections.value.includes(selectedCollection.value) && collections.value.length > 0) {
      selectedCollection.value = collections.value[0];
    }
  } catch (error) {
    console.error("Błąd pobierania plików:", error);
  }
};

const handleCreateCollection = () => {
  const name = prompt("Podaj nazwę nowego katalogu/zbioru:");
  if (name && name.trim()) {
    selectedCollection.value = name.trim();
  }
};

const triggerFileInput = () => fileInputRef.value?.click();

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (!target.files?.length) return;

  isUploading.value = true;
  try {
    const fileList = Array.from(target.files);
    await FileService.uploadFiles(fileList, selectedCollection.value);
    await loadFiles();
  } catch (error) {
    console.error("Błąd uploadu:", error);
    alert("Wystąpił błąd podczas dodawania plików.");
  } finally {
    isUploading.value = false;
    if (fileInputRef.value) fileInputRef.value.value = '';
  }
};

const handleDelete = async (id: string) => {
  if (!confirm("Czy na pewno chcesz usunąć ten plik?")) return;
  try {
    await FileService.deleteFile(id);
    await loadFiles();
  } catch (error) {
    console.error("Błąd usuwania:", error);
  }
};

onMounted(loadFiles);
</script>

<template>
  <div class="flex w-full h-full bg-gray-50 text-gray-800">
    <CollectionSidebar 
      :collections="collections" 
      :selected-collection="selectedCollection"
      @select="(val) => selectedCollection = val"
      @create="handleCreateCollection"
    />

    <main class="flex-1 flex flex-col overflow-hidden">
      <header class="bg-white p-4 border-b border-gray-200 flex justify-between items-center shadow-sm z-10">
        <h1 class="text-xl font-semibold flex items-center">
          <FolderIcon class="w-6 h-6 mr-2 text-indigo-500" />
          Zbiór: {{ selectedCollection }}
        </h1>
        
        <div>
          <input type="file" multiple class="hidden" ref="fileInputRef" @change="handleFileUpload" />
          <button 
            @click="triggerFileInput"
            :disabled="isUploading"
            class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md shadow-sm text-sm font-medium flex items-center disabled:opacity-50 transition-colors"
          >
            <UploadCloudIcon class="w-4 h-4 mr-2" />
            {{ isUploading ? 'Przesyłanie...' : 'Wgraj pliki' }}
          </button>
        </div>
      </header>

      <FileGrid :files="currentFiles" @delete="handleDelete" />
    </main>
  </div>
</template>