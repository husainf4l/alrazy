import type { 
  LoginRequest, 
  LoginResponse, 
  RegisterRequest,
  RegisterResponse,
  User, 
  UpdateUserRequest,
  UserResponse,
  PasswordChangeRequest,
  PasswordChangeResponse,
  PasswordResetRequest,
  PasswordResetResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  CameraResponse,
  Camera,
  CreateCameraRequest,
  UpdateCameraRequest,
  AlertResponse,
  Alert,
  CameraUserAccess
} from '../types/user';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class AuthService {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    // Initialize tokens from cookies on client side
    if (typeof window !== 'undefined') {
      this.accessToken = this.getCookie('access_token');
      this.refreshToken = this.getCookie('refresh_token');
    }
  }

  private setCookie(name: string, value: string, days: number = 7) {
    if (typeof window !== 'undefined') {
      const expires = new Date();
      expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
      // For development, use less strict cookie settings
      const isProduction = window.location.protocol === 'https:';
      const cookieString = isProduction 
        ? `${name}=${value};expires=${expires.toUTCString()};path=/;secure;samesite=strict`
        : `${name}=${value};expires=${expires.toUTCString()};path=/;samesite=lax`;
      
      document.cookie = cookieString;
    }
  }

  private getCookie(name: string): string | null {
    if (typeof window !== 'undefined') {
      const nameEQ = name + "=";
      const ca = document.cookie.split(';');
      
      for(let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) {
          return c.substring(nameEQ.length, c.length);
        }
      }
    }
    return null;
  }

  private deleteCookie(name: string) {
    if (typeof window !== 'undefined') {
      document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
    }
  }

  private setUserData(user: User): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('user_data', JSON.stringify(user));
    }
  }

  private getUserData(): User | null {
    if (typeof window !== 'undefined') {
      const userData = localStorage.getItem('user_data');
      if (userData) {
        try {
          return JSON.parse(userData);
        } catch (error) {
          console.error('Failed to parse user data from localStorage:', error);
          localStorage.removeItem('user_data');
        }
      }
    }
    return null;
  }

  private clearUserData(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('user_data');
      console.log('🗑️ User data cleared from localStorage');
    }
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;

    if (typeof window !== 'undefined') {
      console.log('💾 Storing tokens in cookies...');
      this.setCookie('access_token', accessToken, 7);
      this.setCookie('refresh_token', refreshToken, 30);
      
      // Store token timestamp to track when it was set
      localStorage.setItem('token_timestamp', Date.now().toString());
      console.log('✅ Tokens stored successfully');
    }
  }

  private clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;

    if (typeof window !== 'undefined') {
      this.deleteCookie('access_token');
      this.deleteCookie('refresh_token');
      localStorage.removeItem('token_timestamp');
    }
    this.clearUserData();
  }

  private isAccessTokenLikelyExpired(): boolean {
    if (typeof window === 'undefined') return false;
    
    const tokenTimestamp = localStorage.getItem('token_timestamp');
    if (!tokenTimestamp) return true;
    
    const tokenAge = Date.now() - parseInt(tokenTimestamp);
    // Consider token likely expired if it's older than 55 minutes (assuming 1 hour expiry)
    const maxAge = 55 * 60 * 1000; // 55 minutes in milliseconds
    
    return tokenAge > maxAge;
  }

  private async request(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    // Check if we need to refresh the token before making the request
    if (this.accessToken && this.isAccessTokenLikelyExpired() && this.refreshToken) {
      console.log('🔄 Access token likely expired, refreshing before request...');
      await this.refreshAccessToken();
    }

    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && this.refreshToken) {
      // Try to refresh the token
      console.log('🔄 Got 401, attempting token refresh...');
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        // Retry the original request with new token
        headers['Authorization'] = `Bearer ${this.accessToken}`;
        return fetch(url, { ...options, headers }).then(res => {
          if (!res.ok) {
            return res.json().then(error => Promise.reject(new Error(error.message || `HTTP ${res.status}`)));
          }
          return res.json();
        });
      } else {
        // Refresh failed, redirect to login
        this.clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        throw new Error('Authentication failed');
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'An error occurred' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    console.log('Raw login response from backend:', response);

    // Handle the backend response format: { user, accessToken, refreshToken }
    if (response.accessToken) {
      this.setTokens(response.accessToken, response.refreshToken);
      // Store user data for persistence
      if (response.user) {
        this.setUserData(response.user);
      }
    }

    // Transform backend response to match frontend LoginResponse interface
    const transformedResponse: LoginResponse = {
      success: !!response.user && !!response.accessToken,
      message: response.user ? 'Login successful' : 'Login failed',
      token: response.accessToken,
      refreshToken: response.refreshToken,
      user: response.user
    };

    console.log('Transformed login response:', transformedResponse);
    return transformedResponse;
  }

  async register(userData: RegisterRequest): Promise<RegisterResponse> {
    const response = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });

    console.log('Raw register response from backend:', response);

    // Handle the backend response format: { user, accessToken, refreshToken }
    if (response.accessToken) {
      this.setTokens(response.accessToken, response.refreshToken);
      // Store user data for persistence
      if (response.user) {
        this.setUserData(response.user);
      }
    }

    // Transform backend response to match frontend RegisterResponse interface
    const transformedResponse: RegisterResponse = {
      success: !!response.user && !!response.accessToken,
      message: response.user ? 'Registration successful' : 'Registration failed',
      user: response.user
    };

    console.log('Transformed register response:', transformedResponse);
    return transformedResponse;
  }

  async logout(): Promise<void> {
    try {
      if (this.refreshToken) {
        await this.request('/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refreshToken: this.refreshToken }),
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearTokens();
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      console.log('🔄 Getting current user...');
      console.log('  - Access token present:', !!this.accessToken);
      console.log('  - Refresh token present:', !!this.refreshToken);
      
      // First, try to get cached user data if we have valid tokens
      const cachedUser = this.getUserData();
      if (cachedUser && cachedUser.id && this.accessToken) {
        console.log('✅ Using cached user data with valid access token');
        return cachedUser;
      }
      
      // If we don't have access token but have refresh token, try to refresh
      if (!this.accessToken && this.refreshToken) {
        console.log('🔄 No access token, trying to refresh...');
        const refreshed = await this.refreshAccessToken();
        if (!refreshed) {
          throw new Error('Failed to refresh access token');
        }
        
        // After successful refresh, return cached user if available
        if (cachedUser && cachedUser.id) {
          console.log('✅ Using cached user data after token refresh');
          return cachedUser;
        }
      }
      
      // Only make API call if we don't have cached user data
      if (!cachedUser || !cachedUser.id) {
        console.log('🌐 Fetching user data from API...');
        const response = await this.request('/auth/profile');
        console.log('getCurrentUser API response:', response);
        
        // If the response has a user field, return it, otherwise assume the response IS the user
        const user = response.user || response;
        
        if (!user || !user.id) {
          throw new Error('Invalid user data received from API');
        }
        
        // Store user data for future use
        this.setUserData(user);
        
        return user;
      }
      
      return cachedUser;
    } catch (error) {
      console.error('getCurrentUser error:', error);
      
      // Fallback: try to get user from localStorage if we have valid tokens
      if (this.isAuthenticated()) {
        console.log('🔄 API failed, trying localStorage fallback...');
        const cachedUser = this.getUserData();
        if (cachedUser && cachedUser.id) {
          console.log('✅ Found valid cached user data:', cachedUser);
          return cachedUser;
        }
      }
      
      // If everything fails, throw the error
      throw error;
    }
  }

  async updateProfile(userData: UpdateUserRequest): Promise<UserResponse> {
    return this.request('/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  }

  async changePassword(passwordData: PasswordChangeRequest): Promise<PasswordChangeResponse> {
    return this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(passwordData),
    });
  }

  async requestPasswordReset(data: PasswordResetRequest): Promise<PasswordResetResponse> {
    return this.request('/auth/password-reset', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Camera Management Methods
  async getCameras(): Promise<Camera[]> {
    return this.request('/cameras');
  }

  async getCompanyCameras(companyId: number): Promise<Camera[]> {
    return this.request(`/companies/${companyId}/cameras`);
  }

  async getCamera(id: number): Promise<CameraResponse> {
    return this.request(`/cameras/${id}`);
  }

  async createCamera(cameraData: CreateCameraRequest): Promise<CameraResponse> {
    console.log('AuthService: Creating camera with data:', cameraData);
    console.log('AuthService: API URL:', `${API_BASE_URL}/cameras`);
    
    try {
      const response = await this.request('/cameras', {
        method: 'POST',
        body: JSON.stringify(cameraData),
      });
      console.log('AuthService: Camera creation response:', response);
      return response;
    } catch (error) {
      console.error('AuthService: Camera creation failed:', error);
      throw error;
    }
  }

  async updateCamera(cameraData: UpdateCameraRequest): Promise<CameraResponse> {
    return this.request(`/cameras/${cameraData.id}`, {
      method: 'PUT',
      body: JSON.stringify(cameraData),
    });
  }

  async deleteCamera(id: number): Promise<CameraResponse> {
    return this.request(`/cameras/${id}`, {
      method: 'DELETE',
    });
  }

  // Alert Management Methods
  async getAlerts(): Promise<AlertResponse> {
    return this.request('/alerts');
  }

  async markAlertAsRead(id: number): Promise<AlertResponse> {
    return this.request(`/alerts/${id}/read`, {
      method: 'POST',
    });
  }

  async resolveAlert(id: number): Promise<AlertResponse> {
    return this.request(`/alerts/${id}/resolve`, {
      method: 'POST',
    });
  }

  // Company User Management Methods
  async getCompanyUsers(companyId: number): Promise<User[]> {
    return this.request(`/companies/${companyId}/users`);
  }

  async assignCameraAccess(cameraId: number, userIds: number[], accessLevel: string): Promise<CameraUserAccess> {
    return this.request(`/cameras/${cameraId}/access`, {
      method: 'POST',
      body: JSON.stringify({ userIds, accessLevel }),
    });
  }

  async revokeCameraAccess(cameraId: number, userId: number): Promise<void> {
    return this.request(`/cameras/${cameraId}/access/${userId}`, {
      method: 'DELETE',
    });
  }

  private async refreshAccessToken(): Promise<boolean> {
    try {
      console.log('🔄 Attempting to refresh access token...');
      console.log('  - Refresh token:', this.refreshToken ? 'Present' : 'Missing');
      
      if (!this.refreshToken) {
        console.error('❌ No refresh token available');
        return false;
      }
      
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refreshToken: this.refreshToken }),
      });

      console.log('🔄 Refresh response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Token refresh successful');
        
        // Update tokens with new values
        this.setTokens(data.accessToken, data.refreshToken || this.refreshToken);
        return true;
      } else {
        const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
        console.error('❌ Token refresh failed:', response.status, errorData);
        
        // If refresh token is invalid, clear all tokens
        if (response.status === 401 || response.status === 403) {
          console.log('🧹 Refresh token invalid, clearing all tokens');
          this.clearTokens();
        }
      }
    } catch (error) {
      console.error('❌ Token refresh error:', error);
    }

    return false;
  }

  isAuthenticated(): boolean {
    // Check if we have access token OR refresh token
    const hasAccessToken = !!this.accessToken;
    const hasRefreshToken = !!this.refreshToken;
    
    console.log('🔍 Authentication check:');
    console.log('  - Access token:', hasAccessToken ? 'Present' : 'Missing');
    console.log('  - Refresh token:', hasRefreshToken ? 'Present' : 'Missing');
    
    return hasAccessToken || hasRefreshToken;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }
}

export const authService = new AuthService();
export default AuthService;
