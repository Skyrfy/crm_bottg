import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import Questions from "./components/Questions";
import { HelpCircle } from "lucide-react";
import { apiFetch } from "./config/apiClient";


declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initDataUnsafe?: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
            language_code?: string;
          };
        };
        ready: () => void;
        expand: () => void;
      };
    };
  }
}


export interface UserData {
  student_name: string;
  solved_count: number;
  solved_question_ids: number[];
}


export default function App() {
  const [activeTab, setActiveTab] = useState("questions");
  const [completedQuestions, setCompletedQuestions] = useState<Set<number>>(new Set());
  const [userData, setUserData] = useState<UserData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeTelegram = () => {
      if (window.Telegram?.WebApp) {
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        loadUserData();
      } else if (import.meta.env.DEV) {
        console.warn('⚠️ Running in DEVELOPMENT mode without Telegram');
        loadUserData();
      } else {
        setError('Приложение должно быть открыто через Telegram.');
        setIsLoading(false);
      }
    };

    if (document.readyState === 'complete') {
      initializeTelegram();
    } else {
      window.addEventListener('load', initializeTelegram);
      return () => window.removeEventListener('load', initializeTelegram);
    }
  }, []);

  const loadUserData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await apiFetch('/api/interview/progress/');

      if (!response.ok) {
        if (response.status === 403) {
          setError('Доступ запрещён. Возможно, вы зашли как ментор — этот раздел только для учеников.');
        } else if (response.status === 401) {
          setError('Не удалось проверить ваши данные. Откройте через Telegram.');
        } else {
          setError(`Ошибка загрузки прогресса (${response.status}).`);
        }
        return;
      }

      const data = await response.json();
      setUserData({
        student_name: data.student_name,
        solved_count: data.solved_count,
        solved_question_ids: data.solved_question_ids,
      });
      setCompletedQuestions(new Set(data.solved_question_ids));
    } catch (error) {
      console.error('Error loading user data:', error);
      setError('Ошибка подключения к серверу');
    } finally {
      setIsLoading(false);
    }
  };

  const syncProgress = async (newCompletedQuestions: Set<number>, previousCompletedQuestions: Set<number>) => {
    if (!userData) return;

    try {
      const questions: { question_id: number; is_solved: boolean }[] = [];

      for (const questionId of newCompletedQuestions) {
        if (!previousCompletedQuestions.has(questionId)) {
          questions.push({ question_id: questionId, is_solved: true });
        }
      }
      for (const questionId of previousCompletedQuestions) {
        if (!newCompletedQuestions.has(questionId)) {
          questions.push({ question_id: questionId, is_solved: false });
        }
      }

      if (questions.length === 0) return;

      const response = await apiFetch('/api/interview/progress/', {
        method: 'POST',
        body: JSON.stringify({ questions }),
      });

      if (!response.ok) {
        console.error('Failed to sync progress', response.status);
      }
    } catch (error) {
      console.error('Error syncing progress:', error);
    }
  };

  const handleCompletedQuestionsChange = (
    newCompletedQuestionsOrUpdater: Set<number> | ((prev: Set<number>) => Set<number>)
  ) => {
    const previousCompletedQuestions = new Set<number>(completedQuestions);

    const newCompletedQuestions =
      typeof newCompletedQuestionsOrUpdater === 'function'
        ? newCompletedQuestionsOrUpdater(completedQuestions)
        : newCompletedQuestionsOrUpdater;

    setCompletedQuestions(newCompletedQuestions);
    syncProgress(newCompletedQuestions, previousCompletedQuestions);
  };

  const goToDeadlines = () => {
    window.location.href = '/student/';
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Загружаем ваш прогресс...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <p className="text-red-500 mb-4">{error}</p>
          <p className="text-sm text-muted-foreground">
            Откройте приложение через бота в Telegram
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="max-w-md mx-auto bg-background w-full flex flex-col h-screen">
        {/* User Info Header */}
        {userData && (
          <div className="p-4 border-b bg-primary/5 flex-shrink-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">Привет, {userData.student_name}!</h3>
            </div>
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden relative">
          <div className="flex-1 overflow-auto pb-20">
            <TabsContent value="questions" className="m-0">
              <Questions
                completedQuestions={completedQuestions}
                setCompletedQuestions={handleCompletedQuestionsChange}
              />
            </TabsContent>
          </div>

          {/* Bottom Navigation: Дедлайны / Тренажёр */}
          <div className="fixed bottom-0 left-0 right-0 border-t bg-background shadow-[0_-2px_10px_rgba(0,0,0,0.1)] z-50">
            <div className="grid w-full grid-cols-2 h-16">
              <button
                onClick={goToDeadlines}
                className="flex flex-col items-center justify-center gap-1 hover:bg-primary/10 transition-colors"
              >
                <span className="text-xl">📋</span>
                <span className="text-xs">Дедлайны</span>
              </button>

              <TabsList className="grid grid-cols-1 h-full bg-transparent rounded-none p-0">
                <TabsTrigger
                  value="questions"
                  className="flex flex-col gap-1 data-[state=active]:bg-primary/10 rounded-none h-full"
                >
                  <HelpCircle className="w-5 h-5" />
                  <span className="text-xs">Тренажёр</span>
                </TabsTrigger>
              </TabsList>
            </div>
          </div>
        </Tabs>
      </div>
    </div>
  );
}