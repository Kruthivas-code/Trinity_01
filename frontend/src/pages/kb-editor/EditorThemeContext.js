import { createContext, useContext } from 'react';

const EditorThemeContext = createContext('dark');

export const EditorThemeProvider = EditorThemeContext.Provider;

export const useEditorTheme = () => useContext(EditorThemeContext);
