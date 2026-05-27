// Módulo singleton que guarda o Firebase ID token em memória.
// AuthProvider chama set() a cada renovação de token.
// api.ts e useSSE chamam get() para injetar o token nas requisições.

let _token = process.env.NEXT_PUBLIC_AUTH_BYPASS === "1" ? "local-dev" : "";

export const tokenStore = {
  get: () => _token,
  set: (t: string) => {
    _token = t;
  },
};
