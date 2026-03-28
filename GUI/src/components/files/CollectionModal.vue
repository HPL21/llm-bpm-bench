<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { XIcon } from 'lucide-vue-next';

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'confirm', name: string): void;
}>();

const collectionName = ref('');
const inputRef = ref<HTMLInputElement | null>(null);

const handleConfirm = () => {
  if (collectionName.value.trim()) {
    emit('confirm', collectionName.value.trim());
    collectionName.value = '';
  }
};

const handleClose = () => {
  collectionName.value = '';
  emit('close');
};

import { watch } from 'vue';
watch(() => props.isOpen, async (newVal) => {
  if (newVal) {
    await nextTick();
    inputRef.value?.focus();
  }
});
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm transition-opacity">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden transform transition-all">
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
        <h3 class="text-lg font-semibold text-gray-800">Nowy katalog</h3>
        <button @click="handleClose" class="text-gray-400 hover:text-gray-600 transition-colors">
          <XIcon class="w-5 h-5" />
        </button>
      </div>
      
      <div class="p-6">
        <label for="collectionName" class="block text-sm font-medium text-gray-700 mb-2">
          Nazwa katalogu (zbioru testowego)
        </label>
        <input 
          id="collectionName"
          ref="inputRef"
          v-model="collectionName" 
          type="text" 
          placeholder="np. testy-logika-biznesowa"
          @keyup.enter="handleConfirm"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-shadow"
        />
      </div>
      
      <div class="px-6 py-4 bg-gray-50 flex justify-end space-x-3 border-t border-gray-100">
        <button 
          @click="handleClose" 
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Anuluj
        </button>
        <button 
          @click="handleConfirm" 
          :disabled="!collectionName.trim()"
          class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          Utwórz
        </button>
      </div>
    </div>
  </div>
</template>