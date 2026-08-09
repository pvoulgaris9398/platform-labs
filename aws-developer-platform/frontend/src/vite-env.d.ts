/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MINISTACK_ENDPOINT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
