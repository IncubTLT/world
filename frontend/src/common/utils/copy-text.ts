export async function copyText(text: string | number, callback?: () => void) {
	try {
		if (navigator?.clipboard.writeText) {
			await navigator.clipboard.writeText(
				typeof text === "string" ? text.replace(/^"(.*)"$/, "$1") : String(text)
			);
			if (callback) {
				callback();
			}
		} else {
			console.log("provider no have clipboard copy");
		}
	} catch (_error) {
		console.error("copy error");
	}
}
