import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowRight, Film, Clapperboard, Star, Loader2, User } from 'lucide-react';
import { usePersonDetails } from '../hooks/usePersonDetails';
import { getTmdbImageUrl } from '../types/api';

export const PersonDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { person, castWorks, crewWorks, isLoading, isError, error } = usePersonDetails(id);
  const [activeTab, setActiveTab] = useState<'CREW' | 'CAST'>('CREW');

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center gap-3 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-shelf-amber" />
        <span className="text-sm">در حال دریافت بیوگرافی و فیلم‌شناسی...</span>
      </div>
    );
  }

  if (isError || !person) {
    return (
      <div className="p-8 text-center bg-shelf-card border border-shelf-border rounded-2xl max-w-md mx-auto space-y-4">
        <p className="text-red-400 font-bold text-sm">شخص مورد نظر یافت نشد</p>
        <p className="text-xs text-slate-400">
          {(error as any)?.message || 'اطلاعات این هنرمند در سیستم ثبت نشده است.'}
        </p>
        <Link
          to="/"
          className="inline-block px-4 py-2 rounded-lg bg-slate-800 text-xs text-slate-200 hover:text-white"
        >
          بازگشت به کتابخانه
        </Link>
      </div>
    );
  }

  const defaultTab = crewWorks.length > 0 ? 'CREW' : 'CAST';
  const currentTab = (crewWorks.length === 0 && activeTab === 'CREW') ? 'CAST' : activeTab || defaultTab;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Top Back Navigation Button */}
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-300 hover:text-shelf-amber bg-shelf-card border border-shelf-border px-3.5 py-2 rounded-lg transition"
        >
          <ArrowRight className="w-4 h-4" />
          <span>بازگشت به کتابخانه</span>
        </Link>
      </div>

      {/* Person Bio Hero */}
      <div className="bg-shelf-card border border-shelf-border rounded-2xl p-6 flex flex-col sm:flex-row gap-6 items-center sm:items-start shadow-xl">
        <div className="w-32 h-40 sm:w-40 sm:h-52 rounded-xl overflow-hidden bg-slate-900 border border-white/10 shrink-0 shadow-lg">
          {person.profile_path ? (
            <img
              src={getTmdbImageUrl(person.profile_path, 'w300')}
              alt={person.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-600">
              <User className="w-12 h-12" />
            </div>
          )}
        </div>

        <div className="flex-1 text-center sm:text-right space-y-3">
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
              {person.persian_name || person.name}
            </h1>
            {person.persian_name && (
              <p className="text-sm text-slate-400 font-mono" dir="ltr">
                {person.name}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 pt-1">
            {person.known_for_department && (
              <span className="px-3 py-1 rounded-lg bg-shelf-amber/15 text-shelf-amber border border-shelf-amber/30 text-xs font-medium">
                {person.known_for_department === 'Directing'
                  ? 'کارگردان'
                  : person.known_for_department === 'Acting'
                  ? 'بازیگر'
                  : person.known_for_department}
              </span>
            )}
            <span className="px-3 py-1 rounded-lg bg-slate-800 text-slate-300 text-xs">
              {crewWorks.length + castWorks.length} اثر در آرشیو
            </span>
            <span className="px-2 py-1 rounded-lg bg-shelf-bg border border-shelf-border text-[11px] font-mono text-slate-400" dir="ltr">
              TMDB: {person.tmdb_person_id}
            </span>
          </div>
        </div>
      </div>

      {/* Filmography Section with Tabs */}
      <section className="space-y-6">
        {/* Clean Tabs Header */}
        <div className="flex items-center gap-3 border-b border-shelf-border pb-3">
          {crewWorks.length > 0 && (
            <button
              onClick={() => setActiveTab('CREW')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition ${
                currentTab === 'CREW'
                  ? 'bg-shelf-amber text-black shadow-md shadow-shelf-amber/10'
                  : 'bg-shelf-card text-slate-400 hover:text-white border border-shelf-border'
              }`}
            >
              <Clapperboard className="w-4 h-4" />
              <span>آثار به عنوان کارگردان / عوامل ({crewWorks.length})</span>
            </button>
          )}

          {castWorks.length > 0 && (
            <button
              onClick={() => setActiveTab('CAST')}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition ${
                currentTab === 'CAST'
                  ? 'bg-shelf-amber text-black shadow-md shadow-shelf-amber/10'
                  : 'bg-shelf-card text-slate-400 hover:text-white border border-shelf-border'
              }`}
            >
              <Film className="w-4 h-4" />
              <span>آثار به عنوان بازیگر ({castWorks.length})</span>
            </button>
          )}
        </div>

        {/* Works Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
          {(currentTab === 'CREW' ? crewWorks : castWorks).map((credit) => {
            const movie = credit.work;
            const subtitle =
              credit.credit_type === 'CREW'
                ? credit.job || credit.department
                : credit.character_name
                ? `در نقش ${credit.character_name}`
                : 'بازیگر';

            return (
              <Link
                to={`/works/${movie.id}`}
                key={credit.id}
                className="group bg-shelf-card border border-shelf-border rounded-xl overflow-hidden hover:border-shelf-amber/60 transition shadow-lg flex flex-col"
              >
                <div className="relative aspect-[2/3] bg-slate-900 overflow-hidden">
                  <img
                    src={getTmdbImageUrl(movie.poster_path, 'w500')}
                    alt={movie.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute bottom-2 inset-x-2 flex items-center justify-between text-xs text-white">
                    <span className="font-mono text-slate-300 text-[11px]">
                      {movie.release_year || '—'}
                    </span>
                    {(movie.imdb_rating || movie.tmdb_rating) && (
                      <span className="flex items-center gap-1 bg-black/60 px-1.5 py-0.5 rounded font-mono text-amber-400 text-xs">
                        <Star className="w-3 h-3 fill-amber-400" />
                        {movie.imdb_rating || movie.tmdb_rating}
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-3 flex-1 flex flex-col justify-between space-y-1">
                  <div>
                    <h3 className="font-bold text-xs text-white group-hover:text-shelf-amber transition line-clamp-1">
                      {movie.persian_title || movie.title}
                    </h3>
                    <p className="text-[11px] text-slate-400 font-mono truncate" dir="ltr">
                      {movie.title}
                    </p>
                  </div>
                  <div className="text-[11px] text-shelf-amber pt-1 truncate">
                    {subtitle}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
};
