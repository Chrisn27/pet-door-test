export interface Detection {
  id: string;
  timestamp: string;
  category: 'cats' | 'dogs' | 'unknown';
  detections: PetDetection[];
  filename: string;
  image_url: string;
}

export interface PetDetection {
  type: 'cat' | 'dog';
  confidence: number;
  bbox: number[];
}

export interface SystemStatus {
  active: boolean;
  storage_used_gb: number;
  storage_limit_gb: number;
  fps: number;
  last_detection: number;
}

export interface Config {
  fps: number;
  resolution: [number, number];
  storage_path: string;
  high_water_mark_gb: number;
  detection_confidence: number;
  motion_threshold: number;
  cooldown_seconds: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
}
