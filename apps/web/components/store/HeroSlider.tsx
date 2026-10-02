"use client";

import { useCallback, useEffect, useState } from "react";
import type { StoreSlide } from "@/lib/store";
import { IconArrowRight, IconChevronLeft, IconChevronRight, IconWhatsapp, useSwipe } from "./ui";

const SLIDE_MS = 5500;

export function HeroSlider({
  slides,
  storeName,
  tagline,
  whatsappHref,
  onCatalog,
}: {
  slides: StoreSlide[];
  storeName: string;
  tagline: string;
  whatsappHref: string;
  onCatalog: () => void;
}) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [progressKey, setProgressKey] = useState(0);
  const count = slides.length;

  const go = useCallback(
    (next: number) => {
      if (count === 0) return;
      setIndex(((next % count) + count) % count);
      setProgressKey((k) => k + 1);
    },
    [count]
  );

  useEffect(() => {
    if (count < 2 || paused) return;
    const id = setTimeout(() => go(index + 1), SLIDE_MS);
    return () => clearTimeout(id);
  }, [index, paused, count, go, progressKey]);

  const swipe = useSwipe(
    () => go(index + 1),
    () => go(index - 1)
  );

  const current = slides[index];
  const title = current?.title || storeName;
  const subtitle = current?.subtitle || tagline;

  return (
    <section
      aria-roledescription="carrossel"
      className="group relative isolate h-[68vh] min-h-[440px] max-h-[680px] w-full overflow-hidden rounded-[28px] bg-[var(--accent)] shadow-[0_30px_80px_-30px_rgba(0,0,0,0.45)]"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => {
        setPaused(false);
        setProgressKey((k) => k + 1);
      }}
      onTouchStart={(e) => {
        setPaused(true);
        swipe.onTouchStart(e);
        e.stopPropagation();
      }}
      onTouchEnd={(e) => {
        swipe.onTouchEnd(e);
        setPaused(false);
        e.stopPropagation();
      }}
    >
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(120%_90%_at_20%_10%,rgba(255,255,255,0.28),transparent_55%),linear-gradient(135deg,var(--accent),#0b0b10)]" />

      {slides.map((slide, i) => (
        <div
          key={`${slide.url}-${i}`}
          aria-hidden={i !== index}
          className={`absolute inset-0 transition-opacity duration-[1100ms] ease-in-out ${
            i === index ? "opacity-100" : "opacity-0"
          }`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={slide.url}
            alt={slide.title || storeName}
            loading={i === 0 ? "eager" : "lazy"}
            className={`h-full w-full object-cover ${i === index ? "animate-kenburns" : ""}`}
          />
        </div>
      ))}

      <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/25 to-black/10" />
      <div className="absolute inset-0 bg-gradient-to-r from-black/35 via-transparent to-transparent" />

      <div className="absolute inset-x-0 bottom-0 p-6 pb-16 sm:p-10 sm:pb-20 lg:p-14 lg:pb-24">
        <div key={`${index}-${title}`} className="max-w-2xl space-y-4 text-white">
          <span className="inline-flex animate-fade-up items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.18em] backdrop-blur-md">
            {storeName}
          </span>
          <h1
            className="animate-fade-up font-[family-name:var(--font-display)] text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl"
            style={{ animationDelay: "80ms" }}
          >
            {title}
          </h1>
          {subtitle && (
            <p
              className="max-w-xl animate-fade-up text-base text-white/80 sm:text-lg"
              style={{ animationDelay: "160ms" }}
            >
              {subtitle}
            </p>
          )}
          <div
            className="flex animate-fade-up flex-wrap gap-3 pt-2"
            style={{ animationDelay: "240ms" }}
          >
            <button
              onClick={onCatalog}
              className="group/btn inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-neutral-900 shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl active:translate-y-0"
            >
              Ver catálogo
              <IconArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
            </button>
            <a
              href={whatsappHref}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-white/35 bg-white/10 px-6 py-3 text-sm font-semibold text-white backdrop-blur-md transition hover:-translate-y-0.5 hover:bg-white/20"
            >
              <IconWhatsapp className="h-4 w-4" />
              Falar no WhatsApp
            </a>
          </div>
        </div>
      </div>

      {count > 1 && (
        <>
          <div className="absolute inset-x-6 bottom-6 flex items-center gap-2 sm:inset-x-10 sm:bottom-8 lg:inset-x-14">
            {slides.map((_, i) => (
              <button
                key={i}
                onClick={() => go(i)}
                aria-label={`Ir para o slide ${i + 1}`}
                className="relative h-1 flex-1 overflow-hidden rounded-full bg-white/30"
              >
                {i < index && <span className="absolute inset-0 bg-white" />}
                {i === index && (
                  <span
                    key={progressKey}
                    className="absolute inset-0 origin-left animate-progress bg-white"
                    style={{ animationPlayState: paused ? "paused" : "running" }}
                  />
                )}
              </button>
            ))}
          </div>
          <button
            onClick={() => go(index - 1)}
            aria-label="Slide anterior"
            className="absolute left-4 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/25 bg-black/25 text-white opacity-0 backdrop-blur-md transition hover:bg-black/45 group-hover:opacity-100 sm:flex"
          >
            <IconChevronLeft className="h-5 w-5" />
          </button>
          <button
            onClick={() => go(index + 1)}
            aria-label="Próximo slide"
            className="absolute right-4 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-white/25 bg-black/25 text-white opacity-0 backdrop-blur-md transition hover:bg-black/45 group-hover:opacity-100 sm:flex"
          >
            <IconChevronRight className="h-5 w-5" />
          </button>
        </>
      )}
    </section>
  );
}
