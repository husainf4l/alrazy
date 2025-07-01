
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authService } from '../services/auth';
import type { 
  User, 
  LoginRequest, 
  LoginResponse,
  RegisterRequest, 
  RegisterResponse,
  PasswordResetRequest,
  PasswordResetResponse,
  PasswordChangeRequest,
  PasswordChangeResponse,
  UpdateUserRequest,
  UserResponse,
  AuthContextType 
} from '../types/user';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = !!user && authService.isAuthenticated();

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      setLoading(true);
      console.log('🚀 Initializing authentication...');
      
      const hasTokens = authService.isAuthenticated();
      console.log('📊 Has tokens:', hasTokens);
      
      if (hasTokens) {
        try {
          // Try to get user data - this will handle token refresh internally if needed
          const userData = await authService.getCurrentUser();
          
          if (userData && userData.id) {
            console.log('✅ User authenticated successfully:', userData);
            setUser(userData);
          } else {
            throw new Error('Invalid user data received');
          }
        } catch (error) {
          console.error('❌ Authentication failed during initialization:', error);
          // Clear all authentication data
          if (typeof window !== 'undefined') {
            localStorage.removeItem('user_data');
          }
          await authService.logout();
          setUser(null);
        }
      } else {
        console.log('📝 No valid tokens found');
        // Clear any stale localStorage data
        if (typeof window !== 'undefined') {
          localStorage.removeItem('user_data');
        }
        setUser(null);
      }
    } catch (error) {
      console.error('💥 Failed to initialize auth:', error);
      // Clear all authentication data on error
      if (typeof window !== 'undefined') {
        localStorage.removeItem('user_data');
      }
      await authService.logout();
      setUser(null);
    } finally {
      setLoading(false);
      console.log('🏁 Authentication initialization complete');
    }
  };

  const login = async (credentials: LoginRequest): Promise<LoginResponse> => {
    setLoading(true);
    try {
      const response = await authService.login(credentials);
      console.log('Login response:', response);
      
      if (response.success && response.user) {
        setUser(response.user);
        // Store user in localStorage for persistence across page refreshes
        if (typeof window !== 'undefined') {
          localStorage.setItem('user_data', JSON.stringify(response.user));
        }
      }
      
      return response;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData: RegisterRequest): Promise<RegisterResponse> => {
    setLoading(true);
    try {
      const response = await authService.register(userData);
      
      if (response.success && response.user) {
        setUser(response.user);
      }
      
      return response;
    } catch (error) {
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    setLoading(true);
    try {
      await authService.logout();
      // Clear localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('user_data');
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      setLoading(false);
    }
  };

  const resetPassword = async (data: PasswordResetRequest): Promise<PasswordResetResponse> => {
    return await authService.requestPasswordReset(data);
  };

  const changePassword = async (data: PasswordChangeRequest): Promise<PasswordChangeResponse> => {
    return await authService.changePassword(data);
  };

  const updateUser = async (data: UpdateUserRequest): Promise<UserResponse> => {
    const response = await authService.updateProfile(data);
    if (response.success && response.user) {
      setUser(response.user);
    }
    return response;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated,
        login,
        register,
        logout,
        resetPassword,
        changePassword,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
