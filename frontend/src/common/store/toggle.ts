import { create } from "zustand";

export interface toggleState {
	isOpen: boolean;
	open: () => void;
	close: () => void;
}

export interface toggleStateId extends toggleState {
	id: string | number;
	openId: (id: string | number) => void;
}

export interface customToggleStateId<Id> extends toggleState {
	id: Id;
	openId: (id: Id) => void;
}

export const usePopupComponent = create<toggleState>((set) => ({
	isOpen: false,
	open: () => set({ isOpen: true }),
	close: () => set({ isOpen: false }),
}));

export const useEnergyBayedComponent = create<toggleStateId>((set) => ({
	isOpen: false,
	open: () => set({ isOpen: true }),
	close: () => set({ isOpen: false }),
	openId: (id: string | number) => set({ isOpen: true, id }),
	id: "",
}));
