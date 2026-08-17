import React, { useState, useRef, useEffect } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import Sidebar from './components/Sidebar';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{
    text: string;
    distance: number;
  }>;
}

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleFileUpload = async (file: File) => {
    setIsLoading(true);
    setUploadProgress(0);
    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => (prev < 90 ? prev + 10 : prev));
      }, 200);

      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.ok) {
        const data = await response.json();
        setSelectedFile(file.name);

        // Add system message
        const welcomeMessage: Message = {
          id: Date.now().toString(),
          type: 'assistant',
          content: `✅ Successfully uploaded "${data.filename}". I've processed ${data.num_chunks} chunks from your document. You can now ask questions about it!`,
          timestamp: new Date(),
        };
        setMessages([welcomeMessage]);
      } else {
        const errorMessage: Message = {
          id: Date.now().toString(),
          type: 'assistant',
          content: '❌ Failed to upload file. Please try again.',
          timestamp: new Date(),
        };
        setMessages([errorMessage]);
      }
    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        type: 'assistant',
        content: '❌ Error uploading file. Make sure the backend is running at http://localhost:8000',
        timestamp: new Date(),
      };
      setMessages([errorMessage]);
    } finally {
      setIsLoading(false);
      setUploadProgress(0);
    }
  };

  const handleQuery = async (question: string) => {
    if (!question.trim()) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: question,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      if (response.ok) {
        const data = await response.json();

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: data.answer,
          timestamp: new Date(),
          sources: data.sources,
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: '❌ Failed to get response. Please try again.',
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Query error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: '❌ Error connecting to backend. Make sure the FastAPI server is running.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setSelectedFile(null);
  };

  return (
    <div className="app-container">
      <Sidebar selectedFile={selectedFile} onNewChat={handleNewChat} />
      
      <div className="main-content">
        {messages.length === 0 && !selectedFile ? (
          <FileUpload onFileSelect={handleFileUpload} isLoading={isLoading} uploadProgress={uploadProgress} />
        ) : (
          <ChatInterface messages={messages} isLoading={isLoading} onSendMessage={handleQuery} chatEndRef={chatEndRef} />
        )}
      </div>
    </div>
  );
};

export default App;
