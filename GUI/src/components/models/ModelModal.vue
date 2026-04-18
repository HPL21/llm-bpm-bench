<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { XIcon } from 'lucide-vue-next';
import type { LLMModelCreate, LLMModel } from '../../services/api';

const props = defineProps<{
  isOpen: boolean;
  modelToEdit?: LLMModel | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'save', data: LLMModelCreate): void;
}>();

const formData = ref<LLMModelCreate>({
  name: '',
  provider: '',
  api_base_url: '',
  model_identifier: '',
  api_key: '',
  parameters: {},
  is_active: true
});

const parametersString = ref('');
const inputRef = ref<HTMLInputElement | null>(null);

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    if (props.modelToEdit) {
      formData.value = { ...props.modelToEdit, api_key: props.modelToEdit.api_key || '' };
      parametersString.value = Object.keys(props.modelToEdit.parameters || {}).length > 0 
        ? JSON.stringify(props.modelToEdit.parameters, null, 2) 
        : '';
    } else {
      formData.value = { name: '', provider: 'llama.cpp', api_base_url: '', model_identifier: '', api_key: '', parameters: {}, is_active: true };
      parametersString.value = '';
    }
    await nextTick();
    inputRef.value?.focus();
  }
});

const handleSave = () => {
  if (formData.value.name.trim() && formData.value.provider.trim()) {
    let parsedParams = {};
    if (parametersString.value.trim()) {
      try {
        parsedParams = JSON.parse(parametersString.value);
      } catch (e) {
        alert("Błędny format JSON w parametrach!");
        return;
      }
    }
    emit('save', { ...formData.value, parameters: parsedParams });
  }
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
        <h3 class="text-lg font-semibold text-gray-800">
          {{ modelToEdit ? 'Edytuj Model LLM' : 'Nowy Model LLM' }}
        </h3>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600">
          <XIcon class="w-5 h-5" />
        </button>
      </div>
      
      <div class="p-6 flex-1 overflow-y-auto space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Nazwa wyświetlana *</label>
            <input ref="inputRef" v-model="formData.name" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="np. GPT-4o" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Dostawca (Provider) *</label>
            <input v-model="formData.provider" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="np. openai, anthropic, lokalny" />
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">URL API (Base URL) *</label>
            <input v-model="formData.api_base_url" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="https://api.openai.com/v1" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Identyfikator Modelu *</label>
            <input v-model="formData.model_identifier" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="gpt-4o" />
          </div>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Klucz API (API Key)</label>
          <input v-model="formData.api_key" type="password" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="Zostaw puste jeśli bez uwierzytelniania" />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Dodatkowe parametry (JSON)</label>
          <textarea v-model="parametersString" rows="3" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-mono text-sm" placeholder='{"temperature": 0.7}'></textarea>
        </div>

        <div class="flex items-center mt-4">
          <input v-model="formData.is_active" id="is_active" type="checkbox" class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500">
          <label for="is_active" class="ml-2 block text-sm text-gray-900">Model aktywny</label>
        </div>
      </div>
      
      <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end space-x-3">
        <button @click="emit('close')" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">Anuluj</button>
        <button @click="handleSave" :disabled="!formData.name.trim() || !formData.model_identifier.trim()" class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed">
          Zapisz model
        </button>
      </div>
    </div>
  </div>
</template>