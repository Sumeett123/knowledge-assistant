import React, { useState } from 'react';
import { Send, Loader, MessageCircle, Sparkles, List, Lightbulb, FileText, GraduationCap, Table2 } from 'lucide-react';
import './ChatInterface.css';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Array<{
    text: string;
    distance: number;
    filename?: string;
    page?: number | null;
  }>;
}

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string, previousAnswer?: string) => void;
  chatEndRef: React.RefObject<HTMLDivElement>;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  isLoading,
  onSendMessage,
  chatEndRef,
}) => {
  const [inputValue, setInputValue] = useState('');
  const [followUpAnswer, setFollowUpAnswer] = useState<string | undefined>();

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      onSendMessage(inputValue, followUpAnswer);
      setInputValue('');
      setFollowUpAnswer(undefined);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const explainSimply = (answer: string) => {
    onSendMessage('Explain this answer in simpler words.', answer);
  };

  const rewriteAnswer = (answer: string, request: string) => {
    onSendMessage(request, answer);
  };

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="header-content">
          <h1>Chat with your Document</h1>
          <p>Ask questions and get instant answers with source citations</p>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message-group ${message.type}`}>
            <div className={`message ${message.type}`}>
              <div className="message-avatar">
                {message.type === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content-wrapper">
                <div className="message-bubble">
                  <p className="message-text" style={{ whiteSpace: 'pre-wrap' }}>{message.content}</p>
                  <span className="message-time">
                    {message.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>

                {message.type === 'assistant' && !isLoading && (
                  <div className="answer-actions">
                    <button className="answer-action" onClick={() => explainSimply(message.content)}>
                      <Sparkles size={15} /> Explain simply
                    </button>
                    <button
                      className="answer-action"
                      onClick={() => setFollowUpAnswer(message.content)}
                    >
                      <MessageCircle size={15} /> Ask follow-up
                    </button>
                    <button className="answer-action" onClick={() => rewriteAnswer(message.content, 'Give this answer as key bullet points.')}>
                      <List size={15} /> Key points
                    </button>
                    <button className="answer-action" onClick={() => rewriteAnswer(message.content, 'Give a simple example for this answer.')}>
                      <Lightbulb size={15} /> Example
                    </button>
                    <button className="answer-action" onClick={() => rewriteAnswer(message.content, 'Make this an exam-style answer.')}>
                      <FileText size={15} /> Exam answer
                    </button>
                    <button className="answer-action" onClick={() => rewriteAnswer(message.content, 'Explain for a school student.')}>
                      <GraduationCap size={15} /> School student
                    </button>
                    <button className="answer-action" onClick={() => rewriteAnswer(message.content, 'Compare in a table.')}>
                      <Table2 size={15} /> Table
                    </button>
                  </div>
                )}

                {message.sources && message.sources.length > 0 && (
                  <div className="sources-container">
                    <h4 className="sources-title">📚 Sources</h4>
                    <div className="sources-list">
                      {message.sources.map((source, index) => (
                        <div key={index} className="source-card">
                          <div className="source-header">
                            <span className="source-number">
                              {source.filename ? `${source.filename}${source.page ? ` · p. ${source.page}` : ''}` : `Source ${index + 1}`}
                            </span>
                            <span className="source-distance">
                              Confidence: {(100 - source.distance * 100).toFixed(1)}%
                            </span>
                          </div>
                          <p className="source-text">{source.text.substring(0, 300)}...</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message-group assistant">
            <div className="message assistant">
              <div className="message-avatar">🤖</div>
              <div className="message-content-wrapper">
                <div className="message-bubble loading">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="input-wrapper">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={followUpAnswer ? 'Ask a follow-up about the selected answer...' : 'Ask a question about your document... (Shift + Enter for new line)'}
            disabled={isLoading}
            className="chat-input"
            rows={1}
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="send-button"
          >
            {isLoading ? <Loader size={20} className="loading-icon" /> : <Send size={20} />}
          </button>
        </div>
        <p className="input-hint">Press Enter to send, Shift + Enter for new line. You can ask up to four questions at once.</p>
      </div>
    </div>
  );
};

export default ChatInterface;
