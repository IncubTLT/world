'use client'
// import { useTelegramStore } from "@/common/store/telegram";
import { WebApp } from "@/lib/expand-telegram";

export function DevBackButton({
    action
}:{
    action: () => void;
}) {

    const handleClick = () => {
        action();
    };

    return (
        <button
            className="fixed top-4 z-50 right-4 px-4 py-2 text-sm font-medium text-white bg-gray-700 rounded"
            onClick={handleClick}
        >
            Back
        </button>
    )
}

export function DevMainButton() {
    // const { text } = useTelegramStore();
    const webApp = WebApp();

    const handleClick = () => {
        webApp?.MainButton.show();
    };

    return (
        <button
            className="fixed bottom-0 w-full py-4 text-sm font-medium text-center text-white bg-button_color"
            onClick={handleClick}
        >
            {/* {text} */}
        </button>
    );
}
