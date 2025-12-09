'use client'
import { useEffect } from "react";
import { WebApp } from "@/lib/expand-telegram";

export function ChangeText() {
    // const { text } = useTelegramStore();
    const webApp = WebApp();

    // useEffect(() => {
    //     if (webApp) {
    //         webApp.MainButton.text = text.toUpperCase();
    //     }
    //     // eslint-disable-next-line react-hooks/exhaustive-deps
    // }, [text]);

    return null;
}