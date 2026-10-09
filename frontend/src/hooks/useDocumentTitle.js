import { useEffect } from 'react';

export function useDocumentTitle(title) {
  useEffect(() => {
    if (title) {
      document.title = `${title} | CancelFill`;
    } else {
      document.title = 'CancelFill';
    }
  }, [title]);
}

export default useDocumentTitle;
