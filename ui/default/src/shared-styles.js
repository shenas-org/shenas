import { css } from "lit";

export const tableStyles = css`
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th {
    text-align: left;
    padding: 0.4rem 0.6rem;
    color: #666;
    font-weight: 500;
    border-bottom: 1px solid #e0e0e0;
  }
  td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid #f0f0f0;
  }
`;

export const buttonStyles = css`
  button {
    padding: 0.3rem 0.7rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: #fff;
    cursor: pointer;
    font-size: 0.8rem;
  }
  button:hover {
    background: #f5f5f5;
  }
  button.danger {
    color: #c00;
    border-color: #e8c0c0;
  }
  button.danger:hover {
    background: #fef0f0;
  }
`;

export const tabStyles = css`
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid #e0e0e0;
    margin: 1rem 0;
  }
  .tab {
    padding: 0.5rem 1rem;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 0.9rem;
    color: #666;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    text-decoration: none;
  }
  .tab:hover {
    color: #222;
  }
  .tab[aria-selected="true"] {
    color: #222;
    border-bottom-color: #0066cc;
    font-weight: 600;
  }
`;

export const messageStyles = css`
  .message {
    padding: 0.5rem 0.8rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
  }
  .message.success {
    background: #e8f5e9;
    color: #2e7d32;
  }
  .message.error {
    background: #fce4ec;
    color: #c62828;
  }
`;

export const utilityStyles = css`
  .loading {
    color: #888;
    font-style: italic;
  }
  .empty {
    color: #888;
    padding: 0.5rem 0;
  }
`;

export const linkStyles = css`
  a {
    color: #0066cc;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;
