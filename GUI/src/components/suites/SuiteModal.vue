<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { XIcon } from 'lucide-vue-next';
import type { TestSuiteCreate, TestSuite } from '../../services/api';

const props = defineProps<{
  isOpen: boolean;
  suiteToEdit?: TestSuite | null;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'save', data: TestSuiteCreate): void;
}>();

const formData = ref<TestSuiteCreate>({
  name: '',
  description: '',
  system_prompt: '',
  verification_method: 'EXACT_MATCH'
});

const parametersString = ref('');

const verificationMethods = [
  { value: 'EXACT_MATCH', label: 'Dokładne dopasowanie tekstu' },
  { value: 'JSON_COMPARE', label: 'Porównanie struktury i wartości JSON' },
  { value: 'OCR_MATCH', label: 'Dopasowanie OCR (ignoruj formatowanie)' },
  { value: 'LLM_EVAL', label: 'Ocena przy pomocy LLM jako sędziego' }
];

const inputRef = ref<HTMLInputElement | null>(null);

watch(() => props.isOpen, async (isOpen) => {
  if (isOpen) {
    if (props.suiteToEdit) {
      formData.value = { ...props.suiteToEdit, description: props.suiteToEdit.description || '' };
      parametersString.value = props.suiteToEdit.parameters ? JSON.stringify(props.suiteToEdit.parameters, null, 2) : '';
    } else {
      formData.value = { name: '', description: '', system_prompt: '', verification_method: 'EXACT_MATCH' };
      parametersString.value = '';
    }
    await nextTick();
    inputRef.value?.focus();
  }
});

const handleSave = () => {
  if (formData.value.name.trim() && formData.value.system_prompt.trim()) {
    let parsedParams = null;
    if (parametersString.value.trim()) {
      try {
        parsedParams = JSON.parse(parametersString.value);
      } catch (e) {
        alert("Błędny format JSON w parametrach! Sprawdź składnię.");
        return;
      }
    }
    emit('save', { ...formData.value, parameters: parsedParams });
  }
};
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
      <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
        <h3 class="text-lg font-semibold text-gray-800">
          {{ suiteToEdit ? 'Edytuj zbiór testowy' : 'Nowy zbiór testowy' }}
        </h3>
        <button @click="emit('close')" class="text-gray-400 hover:text-gray-600">
          <XIcon class="w-5 h-5" />
        </button>
      </div>
      
      <div class="p-6 flex-1 overflow-y-auto space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Nazwa zbioru *</label>
          <input ref="inputRef" v-model="formData.name" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" placeholder="np. Ekstrakcja danych z faktur" />
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Opis (opcjonalny)</label>
          <textarea v-model="formData.description" rows="2" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none resize-none" placeholder="Krótki cel tych testów..."></textarea>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Metoda weryfikacji *</label>
          <select v-model="formData.verification_method" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none bg-white">
            <option v-for="method in verificationMethods" :key="method.value" :value="method.value">
              {{ method.label }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">System Prompt *</label>
          <p class="text-xs text-gray-500 mb-2">Instrukcja główna, która zostanie wysłana do LLMa podczas wykonywania tego zbioru testów.</p>
          <textarea v-model="formData.system_prompt" rows="5" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-mono text-sm" placeholder="Jesteś asystentem AI. Twoim zadaniem jest..."></textarea>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Parametry (JSON, opcjonalnie)</label>
          <p class="text-xs text-gray-500 mb-2">Opcjonalne nadpisania parametrów dla tego zbioru. Wymagany poprawny JSON.</p>
          <textarea v-model="parametersString" rows="3" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none font-mono text-sm" placeholder='{"temperature": 0.5}'></textarea>
        </div>
      </div>
      
      <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end space-x-3">
        <button @click="emit('close')" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">Anuluj</button>
        <button @click="handleSave" :disabled="!formData.name.trim() || !formData.system_prompt.trim()" class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed">
          Zapisz zbiór
        </button>
      </div>
    </div>
  </div>
</template>