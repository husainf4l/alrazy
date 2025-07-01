
// User and Authentication Types based on Prisma schema

export interface User {
  id: number;
  email: string;
  username: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  isActive: boolean;
  role: UserRole;
  companyId?: number;
  createdAt: string;
  updatedAt?: string;
  lastLoginAt?: string;
  
  // Relations
  company?: Company;
  cameraAccess?: CameraUserAccess[];
}

export interface Company {
  id: number;
  name: string;
  description?: string;
  address?: string;
  phone?: string;
  email?: string;
  website?: string;
  isActive: boolean;
  settings?: any;
  createdAt: string;
  updatedAt: string;
}

export interface Camera {
  id: number;
  name: string;
  description?: string;
  location?: string;
  rtspUrl: string;
  username?: string;
  password?: string;
  isActive: boolean;
  companyId: number;
  adminUserId?: number;
  
  // Camera settings
  resolutionWidth: number;
  resolutionHeight: number;
  fps: number;
  quality: number;
  enableMotionDetection: boolean;
  enableRecording: boolean;
  recordingDuration: number;
  
  // Status
  isOnline: boolean;
  lastConnectedAt?: string;
  lastHealthCheck?: string;
  
  createdAt: string;
  updatedAt: string;
  
  // Relations
  company?: Company;
  adminUser?: User;
}

export interface CameraUserAccess {
  id: number;
  cameraId: number;
  userId: number;
  accessLevel: CameraAccessLevel;
  grantedAt: string;
  grantedBy?: number;
  
  // Relations
  camera?: {
    id: number;
    name: string;
    location?: string;
  };
  user?: User;
}

export interface Alert {
  id: number;
  cameraId: number;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  description?: string;
  metadata?: any;
  isRead: boolean;
  isResolved: boolean;
  resolvedBy?: number;
  resolvedAt?: string;
  createdAt: string;
  
  // Relations
  camera?: Camera;
}

export interface Recording {
  id: number;
  cameraId: number;
  fileName: string;
  filePath: string;
  fileSize: string; // BigInt as string
  duration: number;
  startTime: string;
  endTime: string;
  triggerType: RecordingTrigger;
  metadata?: any;
  createdAt: string;
  
  // Relations
  camera?: Camera;
}

// Enums
export enum UserRole {
  SUPER_ADMIN = 'SUPER_ADMIN',
  COMPANY_ADMIN = 'COMPANY_ADMIN',
  MANAGER = 'MANAGER',
  USER = 'USER',
  VIEWER = 'VIEWER'
}

export enum CameraAccessLevel {
  ADMIN = 'ADMIN',
  MANAGER = 'MANAGER',
  OPERATOR = 'OPERATOR',
  VIEWER = 'VIEWER'
}

export enum RecordingTrigger {
  MANUAL = 'MANUAL',
  MOTION_DETECTION = 'MOTION_DETECTION',
  ALERT = 'ALERT',
  SCHEDULE = 'SCHEDULE'
}

export enum AlertType {
  MOTION_DETECTED = 'MOTION_DETECTED',
  CAMERA_OFFLINE = 'CAMERA_OFFLINE',
  STORAGE_FULL = 'STORAGE_FULL',
  UNAUTHORIZED_ACCESS = 'UNAUTHORIZED_ACCESS',
  SYSTEM_ERROR = 'SYSTEM_ERROR',
  CUSTOM = 'CUSTOM'
}

export enum AlertSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

// Authentication Request/Response Types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  token?: string;
  refreshToken?: string;
  user?: User;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  confirmPassword: string;
  firstName?: string;
  lastName?: string;
  phone?: string;
  companyId?: number;
}

export interface RegisterResponse {
  success: boolean;
  message: string;
  user?: User;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetResponse {
  success: boolean;
  message: string;
}

export interface PasswordChangeRequest {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface PasswordChangeResponse {
  success: boolean;
  message: string;
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface RefreshTokenResponse {
  success: boolean;
  token?: string;
  refreshToken?: string;
}

// Camera Management Types
export interface CreateCameraRequest {
  name: string;
  description?: string;
  location: string; // Required in backend
  rtspUrl: string;
  username?: string;
  password?: string;
  companyId: number;
  adminUserId?: number; // Added to match backend
  resolutionWidth?: number;
  resolutionHeight?: number;
  fps?: number;
  quality?: number;
  enableMotionDetection?: boolean;
  enableRecording?: boolean;
  recordingDuration?: number;
}

export interface UpdateCameraRequest extends Partial<CreateCameraRequest> {
  id: number;
}

export interface CameraResponse {
  success: boolean;
  message: string;
  camera?: Camera;
  cameras?: Camera[];
}

// Alert Management Types
export interface CreateAlertRequest {
  cameraId: number;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  description?: string;
  metadata?: any;
}

export interface AlertResponse {
  success: boolean;
  message: string;
  alert?: Alert;
  alerts?: Alert[];
}

// User Management Types
export interface UpdateUserRequest {
  firstName?: string;
  lastName?: string;
  phone?: string;
  email?: string;
}

export interface UserResponse {
  success: boolean;
  message: string;
  user?: User;
  users?: User[];
}

// Auth Context Type
export interface AuthContextType {
  user: User | null;
  login: (credentials: LoginRequest) => Promise<LoginResponse>;
  register: (userData: RegisterRequest) => Promise<RegisterResponse>;
  logout: () => Promise<void>;
  resetPassword: (data: PasswordResetRequest) => Promise<PasswordResetResponse>;
  changePassword: (data: PasswordChangeRequest) => Promise<PasswordChangeResponse>;
  updateUser: (data: UpdateUserRequest) => Promise<UserResponse>;
  loading: boolean;
  isAuthenticated: boolean;
}

// API Response wrapper
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
}
