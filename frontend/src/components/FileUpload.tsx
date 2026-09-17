import React, { useState, useRef } from 'react';
import { Upload } from 'lucide-react';
import './FileUpload.css';

interface FileUploadProps {
  onFileSelect: (files: File[]) => void;
  isLoading: boolean;
  uploadProgress: number;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, isLoading, uploadProgress }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const submitFiles = (selected: File[]) => {
    const invalid = selected.find((file) => file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf'));
    const oversized = selected.find((file) => file.size > 50 * 1024 * 1024);
    const duplicateName = selected.find((file, index) => selected.findIndex((other) => other.name === file.name && other.size === file.size) !== index);
    if (invalid) {
      setValidationError(`“${invalid.name}” is not a PDF file.`);
      return;
    }
    if (oversized) {
      setValidationError(`“${oversized.name}” is larger than the 50 MB limit.`);
      return;
    }
    if (duplicateName) {
      setValidationError(`“${duplicateName.name}” was selected more than once.`);
      return;
    }
    setValidationError('');
    onFileSelect(selected);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) submitFiles(Array.from(files));
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (files && files.length > 0) {
      submitFiles(Array.from(files));
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="file-upload-container">
      <div className="upload-content">
        <div className="upload-header">
          <h1 className="upload-title">Knowledge Assistant</h1>
          <p className="upload-subtitle">Upload your PDF and chat with your documents</p>
        </div>

        <div
          className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${isLoading ? 'loading' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={handleClick}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf"
            onChange={handleFileInputChange}
            disabled={isLoading}
            className="file-input"
          />

          {!isLoading ? (
            <>
              <div className="upload-icon">
                <Upload size={48} />
              </div>
              <h2 className="upload-text">Drag and drop one or more PDFs here</h2>
              <p className="upload-hint">or click to select from your computer</p>
              <p className="upload-support">Supports: PDF files only</p>
              <p className="upload-support">Maximum size: 50 MB per PDF</p>
              {validationError && <p className="upload-error" role="alert">{validationError}</p>}
            </>
          ) : (
            <>
              <div className="loading-spinner"></div>
              <h2 className="upload-text">Processing your document...</h2>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
              </div>
              <p className="upload-hint">{uploadProgress}%</p>
            </>
          )}
        </div>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">📄</div>
            <h3>Multiple PDFs</h3>
            <p>Upload and process multiple documents seamlessly</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔍</div>
            <h3>Intelligent Search</h3>
            <p>Semantic search finds relevant sections instantly</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💡</div>
            <h3>Smart Answers</h3>
            <p>Get accurate answers grounded in your documents</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>Fast Processing</h3>
            <p>Instant responses with source citations</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileUpload;
