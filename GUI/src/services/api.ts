import axios from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

export const api = axios.create({
    baseURL: API_URL,
});

export interface FileAsset {
    id: string;
    filename: string;
    collection_name: string;
    minio_path: string;
    content_type: string;
    created_at: string;
}

export interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string;
  verification_method: string;
  created_at: string;
  updated_at: string | null;
}

export const FileService = {
    async getAllFiles() {
        const response = await api.get<FileAsset[]>('/files/');
        return response.data;
    },
    
    async uploadFiles(files: File[], collectionName: string) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        formData.append('collection_name', collectionName);
        
        const response = await api.post<FileAsset[]>('/files/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    async deleteFile(id: string) {
        await api.delete(`/files/${id}`);
    },

    async createCollection(name: string) {
        const response = await api.post<FileAsset>('/files/collections', { name });
        return response.data;
    },
};

export type TestSuiteCreate = Omit<TestSuite, 'id' | 'created_at' | 'updated_at'>;

export const SuiteService = {
  async getAllSuites() {
    const response = await api.get<TestSuite[]>('/suites/');
    return response.data;
  },
  
  async createSuite(data: TestSuiteCreate) {
    const response = await api.post<TestSuite>('/suites/', data);
    return response.data;
  },
  
  async updateSuite(id: string, data: Partial<TestSuiteCreate>) {
    const response = await api.put<TestSuite>(`/suites/${id}`, data);
    return response.data;
  },
  
  async deleteSuite(id: string) {
    await api.delete(`/suites/${id}`);
  }
};


export interface TestCase {
  id: string;
  suite_id: string;
  input_text: string;
  expected_output: string | null;
  files: FileAsset[];
  created_at: string;
}

export const CaseService = {
  async getSuiteCases(suiteId: string) {
    const response = await api.get<TestCase[]>(`/cases/suite/${suiteId}`);
    return response.data;
  },
  
  async importCsv(suiteId: string, collectionName: string, file: File) {
    const formData = new FormData();
    formData.append('collection_name', collectionName);
    formData.append('file', file);
    
    const response = await api.post(`/cases/suite/${suiteId}/import-csv`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  async deleteCase(caseId: string) {
    await api.delete(`/cases/${caseId}`);
  }
};

export interface TestSuite {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string;
  verification_method: string;
  parameters?: Record<string, any> | null;
  created_at: string;
  updated_at: string | null;
}


export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  api_base_url: string;
  model_identifier: string;
  api_key: string | null;
  parameters: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ModelTestResponse {
  success: boolean;
  response: string | null;
  error: string | null;
}

export type LLMModelCreate = Omit<LLMModel, 'id' | 'created_at' | 'updated_at'>;

export const ModelService = {
  async getAllModels() {
    const response = await api.get<LLMModel[]>('/llm-models/');
    return response.data;
  },
  
  async createModel(data: LLMModelCreate) {
    const response = await api.post<LLMModel>('/llm-models/', data);
    return response.data;
  },
  
  async updateModel(id: string, data: Partial<LLMModelCreate>) {
    const response = await api.patch<LLMModel>(`/llm-models/${id}`, data);
    return response.data;
  },
  
  async deleteModel(id: string) {
    await api.delete(`/llm-models/${id}`);
  },

  async testModel(id: string, prompt: string) {
    const response = await api.post<ModelTestResponse>(`/llm-models/${id}/test`, { prompt });
    return response.data;
  }
};


export interface BenchmarkRunCreate {
  name?: string | null;
  model_ids: string[];
  suite_ids: string[];
}

export interface BenchmarkRun {
  id: string;
  name: string | null;
  status: string;
  total_executions: number;
  created_at: string;
}

export interface BenchmarkExecution {
  id: string;
  test_case_id: string;
  llm_model_id: string;
  status: string;
  response_text: string | null;
  score: number | null;
  error_message: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number | null;
  updated_at: string;
}

export interface BenchmarkRunDetail extends BenchmarkRun {
  completed_executions: number;
  failed_executions: number;
  pending_executions: number;
  executions: BenchmarkExecution[];
}

export const BenchmarkService = {
  async getAllRuns() {
    const response = await api.get<BenchmarkRun[]>('/benchmarks/runs');
    return response.data;
  },
  
  async getRunDetails(id: string) {
    const response = await api.get<BenchmarkRunDetail>(`/benchmarks/runs/${id}`);
    return response.data;
  },
  
  async createRun(data: BenchmarkRunCreate) {
    const response = await api.post<BenchmarkRun>('/benchmarks/runs', data);
    return response.data;
  },
  
  async cancelRun(id: string) {
    const response = await api.post(`/benchmarks/runs/${id}/cancel`);
    return response.data;
  }
};