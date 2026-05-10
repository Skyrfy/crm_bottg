import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Progress } from "./ui/progress";
import { Badge } from "./ui/badge";
import { Trophy, Target } from "lucide-react";
import { UserData } from "../App";
import { API_BASE_URL } from "../config/api";


interface Question {
  id: number;
  title: string;
  company: string;
  answer: string;
  topic: {
    id: number;
    language: string;
    topic: string;
  };
}

interface ProgressStatsProps {
  completedQuestions: Set<number>;
  userData: UserData | null;
}

export default function ProgressStats({ completedQuestions, userData }: ProgressStatsProps) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    const fetchAllQuestions = async () => {
      try {
        let allQuestions: Question[] = [];
        let page = 1;
        let hasMore = true;

        // Fetch all pages
        while (hasMore) {
          const response = await fetch(`${API_BASE_URL}/api/questions/?page=${page}&page_size=100`);
          const data = await response.json();
          
          allQuestions = [...allQuestions, ...data.results];
          hasMore = !!data.next;
          page++;
        }

        setQuestions(allQuestions);
        setTotalCount(allQuestions.length);
      } catch (error) {
        console.error('Error fetching questions:', error);
        setQuestions([]);
      } finally {
        setLoading(false);
      }
    };

    fetchAllQuestions();
  }, []);

  if (loading) {
    return (
      <div className="p-4 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  const totalQuestions = questions.length;
  const questionsAnswered = completedQuestions.size;
  const overallProgress = totalQuestions > 0 ? (questionsAnswered / totalQuestions) * 100 : 0;

  const categoryStats = questions.reduce((acc, question) => {
    const category = question.topic.language;
    const topicName = question.topic.topic;
    
    if (!acc[category]) {
      acc[category] = { total: 0, completed: 0, topics: new Set() };
    }
    
    acc[category].total++;
    acc[category].topics.add(topicName);
    
    if (completedQuestions.has(question.id)) {
      acc[category].completed++;
    }
    
    return acc;
  }, {} as Record<string, { total: number; completed: number; topics: Set<string> }>);

  const categoryProgress = Object.entries(categoryStats)
    .map(([name, stats]) => {
      const typedStats = stats as { total: number; completed: number; topics: Set<string> };
      return {
        name,
        completed: typedStats.completed,
        total: typedStats.total,
        topicsCount: typedStats.topics.size,
        accuracy: typedStats.completed > 0 ? Math.round((typedStats.completed / typedStats.total) * 100) : 0
      };
    })
    .sort((a, b) => b.completed - a.completed); // Sort by number of completed questions

  // Calculate topic stats
  const topicStats = questions.reduce((acc, question) => {
    const topic = question.topic.topic;
    const language = question.topic.language;
    const key = `${language} - ${topic}`;
    
    if (!acc[key]) {
      acc[key] = { total: 0, completed: 0, language, topic };
    }
    acc[key].total++;
    if (completedQuestions.has(question.id)) {
      acc[key].completed++;
    }
    return acc;
  }, {} as Record<string, { total: number; completed: number; language: string; topic: string }>);

  const topTopics = Object.entries(topicStats)
    .sort(
      ([, a], [, b]) =>
        (b as { completed: number; total: number }).completed -
        (a as { completed: number; total: number }).completed
    )
    .slice(0, 5);

  return (
    <div className="p-4 space-y-4">
      <div className="text-center mb-6">
        <h2 className="mb-2">Ваш Прогресс</h2>
        {userData && (
          <p className="text-xs text-muted-foreground mt-2">
            Пользователь: {userData.telegram_handle}
          </p>
        )}
      </div>

      {/* Overall Stats */}
        <Card>
          <CardContent className="p-4 text-center">
            <div className="flex items-center justify-center mb-2">
              <Target className="w-5 h-5 text-primary" />
            </div>
            <div className="text-2xl font-semibold">{questionsAnswered}</div>
            <p className="text-sm text-muted-foreground">Вопросов решено</p>
          </CardContent>
        </Card>

      {/* Category Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Прогресс по языкам программирования</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {categoryProgress.map((category, index) => {
            const progress = (category.completed / category.total) * 100;
            return (
              <div key={index} className="space-y-2">
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-sm font-medium">{category.name}</span>
                    <p className="text-xs text-muted-foreground">
                      {category.topicsCount} тем
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-muted-foreground">
                      {category.completed}/{category.total}
                    </span>
                    <p className="text-xs text-green-600">
                      {category.accuracy}% пройдено
                    </p>
                  </div>
                </div>
                <Progress value={progress} className="h-1.5" />
              </div>
            );
          })}
          {categoryProgress.length === 0 && (
            <p className="text-sm text-muted-foreground text-center">
              Начните решать вопросы, чтобы увидеть прогресс
            </p>
          )}
        </CardContent>
      </Card>

      {/* Top Topics by Completed Questions */}
      {topTopics.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Топ тем по решенным вопросам</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {topTopics.map(([key, stats], index) => {
              const typedStats = stats as { completed: number; total: number; language: string; topic: string };
              const { completed, total, language, topic } = typedStats;
              const progress = total > 0 ? (completed / total) * 100 : 0;
              return (
                <div key={index} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">#{index + 1}</Badge>
                        <p className="text-sm font-medium truncate">{topic}</p>
                      </div>
                      <p className="text-xs text-muted-foreground ml-8">{language}</p>
                    </div>
                    <div className="text-right ml-2">
                      <span className="text-sm font-semibold text-green-600">
                        {completed}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        /{total}
                      </span>
                    </div>
                  </div>
                  <Progress value={progress} className="h-1.5" />
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}
    </div>
  );
}