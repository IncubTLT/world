import axios, { type AxiosInstance } from "axios";

class CoreClient {
	core_backend: AxiosInstance;
	constructor() {
		this.core_backend = axios.create({
			baseURL: process.env.BASE_URL,
		});

		this.#init();
	}

	#get_token() {
		if (typeof window === "undefined") {
			return null;
		}
		return localStorage.getItem("token");
	}

	#init() {
		this.core_backend.interceptors.request.use((config) => {
			const token = this.#get_token();
			if (token) {
				config.headers.Authorization = `Bearer ${token}`;
			}
			return config;
		});

		this.core_backend.interceptors.response.use((response) => {
			return response;
		});
	}
}

export const CORE_CLIENT_BACKEND = new CoreClient();
