import { useState, useEffect } from 'react';
import type { Detection, SystemStatus } from './types';
import { getStatus, getDetections, toggleDetection, deleteDetection } from './api';
import './App.css';

function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'cats' | 'dogs' | 'unknown'>('all');
  const [selectedImage, setSelectedImage] = useState<Detection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await getStatus();
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  };

  const fetchDetections = async () => {
    try {
      setLoading(true);
      const data = await getDetections(selectedCategory, 100);
      setDetections(data.detections);
      setError(null);
    } catch (err) {
      setError('Failed to load detections');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async () => {
    try {
      await toggleDetection();
      await fetchStatus();
    } catch (err) {
      console.error('Failed to toggle detection:', err);
    }
  };

  const handleDelete = async (detection: Detection) => {
    if (!window.confirm('Delete this detection?')) return;

    try {
      await deleteDetection(detection.category, detection.id);
      await fetchDetections();
      if (selectedImage?.id === detection.id) {
        setSelectedImage(null);
      }
    } catch (err) {
      console.error('Failed to delete:', err);
      alert('Failed to delete detection');
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchDetections();

    // Refresh every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchDetections();
    }, 5000);

    return () => clearInterval(interval);
  }, [selectedCategory]);

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const storagePercent = status
    ? Math.round((status.storage_used_gb / status.storage_limit_gb) * 100)
    : 0;

  return (
    <div className="app">
      <header className="header">
        <h1>🐾 Pet Door Monitor</h1>
        
        {status && (
          <div className="status-bar">
            <div className="status-item">
              <span className={`indicator ${status.active ? 'active' : 'inactive'}`} />
              <span>{status.active ? 'Monitoring' : 'Paused'}</span>
            </div>
            
            <div className="status-item">
              <span>Storage: {status.storage_used_gb.toFixed(2)}GB / {status.storage_limit_gb}GB</span>
              <div className="storage-bar">
                <div 
                  className="storage-fill" 
                  style={{ 
                    width: `${storagePercent}%`,
                    backgroundColor: storagePercent > 80 ? '#f44336' : '#4caf50'
                  }} 
                />
              </div>
            </div>
            
            <button 
              className={`toggle-btn ${status.active ? 'active' : ''}`}
              onClick={handleToggle}
            >
              {status.active ? 'Pause' : 'Start'}
            </button>
          </div>
        )}
      </header>

      <div className="main-content">
        <aside className="sidebar">
          <div className="filter-section">
            <h3>Filter by Category</h3>
            <div className="filter-buttons">
              <button
                className={selectedCategory === 'all' ? 'active' : ''}
                onClick={() => setSelectedCategory('all')}
              >
                All ({detections.length})
              </button>
              <button
                className={selectedCategory === 'cats' ? 'active' : ''}
                onClick={() => setSelectedCategory('cats')}
              >
                🐱 Cats
              </button>
              <button
                className={selectedCategory === 'dogs' ? 'active' : ''}
                onClick={() => setSelectedCategory('dogs')}
              >
                🐶 Dogs
              </button>
              <button
                className={selectedCategory === 'unknown' ? 'active' : ''}
                onClick={() => setSelectedCategory('unknown')}
              >
                ❓ Unknown
              </button>
            </div>
          </div>

          {selectedImage && (
            <div className="detail-panel">
              <h3>Detection Details</h3>
              <img 
                src={selectedImage.image_url} 
                alt="Detection"
                className="detail-image"
              />
              <div className="detail-info">
                <p><strong>Time:</strong> {formatDate(selectedImage.timestamp)}</p>
                <p><strong>Category:</strong> {selectedImage.category}</p>
                <p><strong>Detections:</strong> {selectedImage.detections.length}</p>
                {selectedImage.detections.map((det, idx) => (
                  <p key={idx}>
                    {det.type} ({Math.round(det.confidence * 100)}%)
                  </p>
                ))}
              </div>
              <div className="detail-actions">
                <button 
                  className="delete-btn"
                  onClick={() => handleDelete(selectedImage)}
                >
                  Delete
                </button>
                <button onClick={() => setSelectedImage(null)}>Close</button>
              </div>
            </div>
          )}
        </aside>

        <main className="gallery">
          {loading && <div className="loading">Loading...</div>}
          
          {error && <div className="error">{error}</div>}
          
          {!loading && detections.length === 0 && (
            <div className="empty-state">
              <p>No detections yet</p>
              <p>Pet activity will appear here</p>
            </div>
          )}

          <div className="grid">
            {detections.map((detection) => (
              <div
                key={detection.id}
                className={`card ${selectedImage?.id === detection.id ? 'selected' : ''}`}
                onClick={() => setSelectedImage(detection)}
              >
                <img 
                  src={detection.image_url} 
                  alt={`Detection ${detection.id}`}
                  loading="lazy"
                />
                <div className="card-overlay">
                  <div className="card-badge">{detection.category}</div>
                  <div className="card-time">
                    {new Date(detection.timestamp).toLocaleTimeString()}
                  </div>
                  {detection.detections.length > 0 && (
                    <div className="card-count">
                      {detection.detections.length} pet{detection.detections.length > 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
