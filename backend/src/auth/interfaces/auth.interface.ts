export interface JwtPayload {
  sub: number;
  email: string;
  username: string;
  role: string;
  companyId?: number;
}

export interface LoginResponse {
  user: {
    id: number;
    email: string;
    username: string;
    firstName?: string;
    lastName?: string;
    role: string;
    companyId?: number;
  };
  accessToken: string;
  refreshToken: string;
}
