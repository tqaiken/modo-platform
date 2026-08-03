import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { api } from "../services/api";


export type UserRole =
  | "SUPER_ADMIN"
  | "CURATOR"
  | "VERIFIER"
  | "DEVELOPER";


export interface User {
  id: number;
  username: string;
  email: string | null;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  subject_id: number | null;
}


interface AuthContextType {
  user: User | null;
  loading: boolean;

  login: (
    username: string,
    password: string
  ) => Promise<void>;

  logout: () => void;

  refreshUser: () => Promise<void>;

  register: (
    email: string,
    fullName: string,
    password: string,
    role: string
  ) => Promise<void>;
}


const AuthContext = createContext<AuthContextType | null>(
  null
);


function setAuthorizationToken(
  token: string | null
): void {
  if (token) {
    api.defaults.headers.common.Authorization =
      `Bearer ${token}`;

    return;
  }

  delete api.defaults.headers.common.Authorization;
}


export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);

  const [loading, setLoading] = useState(true);


  const refreshUser = useCallback(async (): Promise<void> => {
    const token = localStorage.getItem("token");

    if (!token) {
      setAuthorizationToken(null);
      setUser(null);
      return;
    }

    setAuthorizationToken(token);

    try {
      const response = await api.get<User>(
        "/api/v1/auth/me"
      );

      setUser(response.data);
    } catch {
      localStorage.removeItem("token");
      setAuthorizationToken(null);
      setUser(null);
    }
  }, []);


  useEffect(() => {
    const restoreSession = async (): Promise<void> => {
      try {
        await refreshUser();
      } finally {
        setLoading(false);
      }
    };

    void restoreSession();
  }, [refreshUser]);


  const login = useCallback(
    async (
      username: string,
      password: string
    ): Promise<void> => {
      const normalizedUsername = username
        .trim()
        .toLowerCase();

      const response = await api.post(
        "/api/v1/auth/login",
        {
          username: normalizedUsername,
          password,
        }
      );

      const {
        access_token: accessToken,
        user: userData,
      } = response.data as {
        access_token: string;
        token_type: string;
        user: User;
      };

      localStorage.setItem(
        "token",
        accessToken
      );

      setAuthorizationToken(accessToken);
      setUser(userData);
    },
    []
  );


  const register = useCallback(
    async (
      _email: string,
      _fullName: string,
      _password: string,
      _role: string
    ): Promise<void> => {
      throw new Error(
        "Публичная регистрация отключена. " +
          "Пользователей создаёт супер-администратор."
      );
    },
    []
  );


  const logout = useCallback((): void => {
    localStorage.removeItem("token");
    setAuthorizationToken(null);
    setUser(null);
  }, []);


  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        refreshUser,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth должен использоваться внутри AuthProvider"
    );
  }

  return context;
}