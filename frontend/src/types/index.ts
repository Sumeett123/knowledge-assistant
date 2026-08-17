import React from 'react';

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{
    text: string;
    distance: number;
  }>;
}

export interface APIResponse {
  question: string;
  answer: string;
  sources: Array<{
    text: string;
    distance: number;
  }>;
}

export interface UploadResponse {
  message: string;
  filename: string;
  text_preview: string;
  num_chunks: number;
  sample_chunk: string;
}
