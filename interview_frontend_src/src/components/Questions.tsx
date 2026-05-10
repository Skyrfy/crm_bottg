import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Input } from "./ui/input";
import { ChevronDown, ChevronUp, Search, Filter, Check, Loader2 } from "lucide-react";
import { apiFetch } from "../config/apiClient";

interface QuestionTopic {
  id: number;
  language: string;
  topic: string;
}

interface Question {
  id: number;
  title: string;
  company: string;
  answer: string;
  topic: QuestionTopic;
  language?: string;     // приходят как сериализованные поля топика
  topic_name?: string;
}

interface QuestionsProps {
  completedQuestions: Set<number>;
  setCompletedQuestions: (questions: Set<number> | ((prev: Set<number>) => Set<number>)) => void;
}

interface FilterOptions {
  languages: string[];
  companies: string[];
  topics: string[];
}

export default function Questions({ completedQuestions, setCompletedQuestions }: QuestionsProps) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("all");
  const [selectedCompany, setSelectedCompany] = useState("all");
  const [selectedTopic, setSelectedTopic] = useState("all");
  const [hideCompleted, setHideCompleted] = useState(false);

  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);

  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    languages: [],
    companies: [],
    topics: [],
  });

  const observerTarget = useRef<HTMLDivElement>(null);
  const loadingRef = useRef(false);

  // Загрузка фильтров с бэкенда
  const fetchFilterOptions = useCallback(async () => {
    try {
      const response = await apiFetch('/api/interview/filters/');
      if (!response.ok) return;
      const data = await response.json();
      setFilterOptions(data);
    } catch (error) {
      console.error('Error fetching filter options:', error);
    }
  }, []);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  const fetchQuestions = useCallback(async (pageNum: number, reset: boolean = false) => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setIsLoading(true);

    try {
      const params = new URLSearchParams({
        page: pageNum.toString(),
        page_size: '20',
      });

      if (selectedLanguage !== 'all') params.append('language', selectedLanguage);
      if (selectedCompany !== 'all') params.append('company', selectedCompany);
      if (selectedTopic !== 'all') params.append('topic', selectedTopic);

      const response = await apiFetch(`/api/interview/questions/?${params}`);
      if (!response.ok) {
        console.error('Failed to fetch questions:', response.status);
        return;
      }
      const data = await response.json();

      // Бэкенд отдаёт language и topic_name — нормализуем под ожидаемую форму
      const normalized: Question[] = (data.results || []).map((q: any) => ({
        ...q,
        topic: q.topic && typeof q.topic === 'object'
          ? q.topic
          : { id: q.topic, language: q.language, topic: q.topic_name },
      }));

      setQuestions((prev) => (reset ? normalized : [...prev, ...normalized]));
      setHasMore(!!data.next);
      setTotalCount(data.count);
    } catch (error) {
      console.error('Error fetching questions:', error);
    } finally {
      setIsLoading(false);
      loadingRef.current = false;
    }
  }, [selectedLanguage, selectedCompany, selectedTopic]);

  // Перезагрузка при смене фильтров
  useEffect(() => {
    setPage(1);
    setQuestions([]);
    setHasMore(true);
    fetchQuestions(1, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLanguage, selectedCompany, selectedTopic]);

  // Intersection observer для бесконечной прокрутки
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingRef.current) {
          setPage((prev) => prev + 1);
        }
      },
      { threshold: 0.1 }
    );

    const currentTarget = observerTarget.current;
    if (currentTarget) observer.observe(currentTarget);

    return () => {
      if (currentTarget) observer.unobserve(currentTarget);
    };
  }, [hasMore]);

  useEffect(() => {
    if (page > 1) fetchQuestions(page, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  // Клиентская фильтрация по поиску и галке "скрыть решённые"
  const filteredQuestions = useMemo(() => {
    return questions.filter((question) => {
      const matchesSearch =
        searchTerm === '' ||
        question.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        question.answer.toLowerCase().includes(searchTerm.toLowerCase());
      const notCompleted = !hideCompleted || !completedQuestions.has(question.id);
      return matchesSearch && notCompleted;
    });
  }, [searchTerm, questions, hideCompleted, completedQuestions]);

  const toggleQuestion = (questionId: number) => {
    setExpandedQuestions((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(questionId)) newSet.delete(questionId);
      else newSet.add(questionId);
      return newSet;
    });
  };

  const toggleCompleted = (questionId: number) => {
    const newSet = new Set(completedQuestions);
    if (newSet.has(questionId)) newSet.delete(questionId);
    else newSet.add(questionId);
    setCompletedQuestions(newSet);
  };

  return (
    <div className="p-4 space-y-4">
      <div className="text-center mb-6">
        <h2 className="mb-2">ВОПРОСЫ ИЗ СОБЕСОВ</h2>
        <p className="text-muted-foreground">Тренажёр для подготовки к собеседованиям</p>
      </div>

      {/* Поиск и фильтры */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Найти вопрос..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="grid grid-cols-3 gap-2">
          <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Язык" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все языки</SelectItem>
              {filterOptions.languages.map((lang) => (
                <SelectItem key={lang} value={lang}>{lang}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={selectedCompany} onValueChange={setSelectedCompany}>
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Компания" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все компании</SelectItem>
              {filterOptions.companies.map((company) => (
                <SelectItem key={company} value={company}>{company}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={selectedTopic} onValueChange={setSelectedTopic}>
            <SelectTrigger className="text-sm">
              <SelectValue placeholder="Тема" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все темы</SelectItem>
              {filterOptions.topics.map((topic) => (
                <SelectItem key={topic} value={topic}>{topic}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="col-span-3 flex justify-end">
            <Button
              variant={hideCompleted ? 'default' : 'outline'}
              size="sm"
              className="min-w-[180px] px-6"
              onClick={() => setHideCompleted((h) => !h)}
            >
              {hideCompleted ? 'Показать решённые' : 'Скрыть решённые'}
            </Button>
          </div>
        </div>

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{filteredQuestions.length} из {totalCount} вопросов · {completedQuestions.size} решено</span>
          {(selectedLanguage !== 'all' || selectedCompany !== 'all' || selectedTopic !== 'all' || searchTerm) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchTerm('');
                setSelectedLanguage('all');
                setSelectedCompany('all');
                setSelectedTopic('all');
              }}
            >
              Очистить фильтры
            </Button>
          )}
        </div>
      </div>

      {/* Список вопросов */}
      <div className="space-y-3">
        {filteredQuestions.map((question) => {
          const isExpanded = expandedQuestions.has(question.id);
          const isCompleted = completedQuestions.has(question.id);
          return (
            <Card key={question.id} className={`overflow-hidden ${isCompleted ? 'bg-green-50 border-green-200' : ''}`}>
              <CardHeader className="pb-3">
                <div className="flex items-start gap-3">
                  <Button
                    variant={isCompleted ? 'default' : 'outline'}
                    size="sm"
                    className={`p-2 mt-0.5 flex-shrink-0 ${isCompleted ? 'bg-green-600 hover:bg-green-700' : ''}`}
                    onClick={() => toggleCompleted(question.id)}
                  >
                    <Check className="w-4 h-4" />
                  </Button>

                  <div className="flex-1 min-w-0">
                    <div
                      className="cursor-pointer hover:bg-accent/50 transition-colors rounded p-2 -m-2"
                      onClick={() => toggleQuestion(question.id)}
                    >
                      <CardTitle className={`text-sm leading-relaxed mb-2 ${isCompleted ? 'line-through text-muted-foreground' : ''}`}>
                        {question.title}
                      </CardTitle>
                      <div className="flex flex-wrap gap-1">
                        <Badge variant="secondary" className="text-xs bg-blue-100">
                          {question.topic.language}
                        </Badge>
                        <Badge variant="outline" className="text-xs bg-green-100">
                          {question.topic.topic}
                        </Badge>
                        <Badge variant="outline" className="text-xs bg-yellow-100">
                          {question.company}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    className="p-1 flex-shrink-0 mt-0.5"
                    onClick={() => toggleQuestion(question.id)}
                  >
                    {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </Button>
                </div>
              </CardHeader>

              {isExpanded && (
                <CardContent className="pt-0">
                  <div className="border-t pt-3">
                    <h4 className="mb-2">Рекомендованный ответ:</h4>
                    <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">
                      {question.answer}
                    </p>
                  </div>
                </CardContent>
              )}
            </Card>
          );
        })}

        {isLoading && (
          <div className="flex justify-center py-4">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        )}

        {hasMore && <div ref={observerTarget} className="h-4" />}
      </div>

      {filteredQuestions.length === 0 && !isLoading && (
        <div className="text-center py-8">
          <Filter className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">Вопросы не найдены</p>
          <Button
            variant="outline"
            className="mt-2"
            onClick={() => {
              setSearchTerm('');
              setSelectedLanguage('all');
              setSelectedCompany('all');
              setSelectedTopic('all');
            }}
          >
            Очистить фильтры
          </Button>
        </div>
      )}
    </div>
  );
}