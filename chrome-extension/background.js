const MENU_ID = "forward-check-selection";

chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: MENU_ID,
        title: "Fact-check with Forward Check",
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener((info) => {
    if (info.menuItemId !== MENU_ID || !info.selectionText) {
        return;
    }
    chrome.storage.session.set({
        pendingSelection: info.selectionText.slice(0, 10000)
    });
    chrome.tabs.create({
        url: chrome.runtime.getURL("popup.html?selection=1")
    });
});
