import Next from "next";

declare global {
    namespace NodeJS {
        interface ProcessEnv {
            BASE_URL: string;
            
        }
    }
}