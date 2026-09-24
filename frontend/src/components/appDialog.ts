import {
  createContext,
  useContext,
} from "react";


export type DialogTone =
  | "default"
  | "danger"
  | "success";


export interface BaseDialogOptions {
  title: string;
  description?: string;
  tone?: DialogTone;
}


export interface ConfirmDialogOptions
  extends BaseDialogOptions {
  confirmLabel?: string;
  cancelLabel?: string;
}


export interface PromptDialogOptions
  extends BaseDialogOptions {
  confirmLabel?: string;
  cancelLabel?: string;
  defaultValue?: string;
  placeholder?: string;
}


export interface AlertDialogOptions
  extends BaseDialogOptions {
  actionLabel?: string;
}


export interface AppDialogContextValue {
  confirm: (
    options: ConfirmDialogOptions,
  ) => Promise<boolean>;

  prompt: (
    options: PromptDialogOptions,
  ) => Promise<string | null>;

  alert: (
    options: AlertDialogOptions,
  ) => Promise<void>;
}


export const AppDialogContext =
  createContext<AppDialogContextValue | null>(
    null,
  );


export function useAppDialog() {
  const context =
    useContext(
      AppDialogContext,
    );

  if (!context) {
    throw new Error(
      "useAppDialog must be used inside AppDialogProvider.",
    );
  }

  return context;
}