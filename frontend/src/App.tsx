import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AppLayout } from './components/AppLayout';
import { LibraryPage } from './pages/LibraryPage';
import { MovieDetailsPage } from './pages/MovieDetailsPage';
import { PersonDetailsPage } from './pages/PersonDetailsPage';
import { WatchlistDownloadsPage } from './pages/WatchlistDownloadsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <Routes>
            <Route
              element={
                <AppLayout searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
              }
            >
              <Route path="/" element={<LibraryPage searchQuery={searchQuery} />} />
              <Route path="/works/:id" element={<MovieDetailsPage />} />
              <Route path="/people/:id" element={<PersonDetailsPage />} />
              <Route path="/watchlist" element={<WatchlistDownloadsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
