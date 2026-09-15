const STORAGE_KEY = "todo-list.items.v1";

const form = document.getElementById("todoForm");
const input = document.getElementById("todoInput");
const list = document.getElementById("todoList");
const emptyState = document.getElementById("emptyState");
const taskCount = document.getElementById("taskCount");
const progressValue = document.getElementById("progressValue");
const clearCompleted = document.getElementById("clearCompleted");
const filterButtons = [...document.querySelectorAll(".filter-button")];
const template = document.getElementById("todoItemTemplate");

let todos = loadTodos();
let currentFilter = "all";

function loadTodos() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
}

function saveTodos() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
}

function createTodo(text) {
  return {
    id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
    text,
    completed: false,
    createdAt: Date.now(),
  };
}

function getVisibleTodos() {
  if (currentFilter === "active") {
    return todos.filter((todo) => !todo.completed);
  }

  if (currentFilter === "completed") {
    return todos.filter((todo) => todo.completed);
  }

  return todos;
}

function render() {
  list.replaceChildren();

  const visibleTodos = getVisibleTodos();

  for (const todo of visibleTodos) {
    const fragment = template.content.cloneNode(true);
    const item = fragment.querySelector(".todo-item");
    const checkbox = fragment.querySelector(".todo-checkbox");
    const text = fragment.querySelector(".todo-text");
    const deleteButton = fragment.querySelector(".delete-button");

    item.dataset.id = todo.id;
    item.classList.toggle("completed", todo.completed);
    checkbox.checked = todo.completed;
    checkbox.setAttribute("aria-label", todo.completed ? `标记“${todo.text}”为未完成` : `标记“${todo.text}”为已完成`);
    text.textContent = todo.text;

    checkbox.addEventListener("change", () => toggleTodo(todo.id));
    deleteButton.addEventListener("click", () => deleteTodo(todo.id));

    list.appendChild(fragment);
  }

  const activeCount = todos.filter((todo) => !todo.completed).length;
  const completedCount = todos.length - activeCount;
  const progress = todos.length === 0 ? 0 : Math.round((completedCount / todos.length) * 100);

  taskCount.textContent = `${activeCount} 个待完成任务`;
  progressValue.textContent = `${progress}%`;
  clearCompleted.disabled = completedCount === 0;
  clearCompleted.style.opacity = completedCount === 0 ? "0.45" : "1";

  emptyState.hidden = visibleTodos.length > 0;

  if (visibleTodos.length === 0) {
    const heading = emptyState.querySelector("h2");
    const paragraph = emptyState.querySelector("p");

    if (currentFilter === "active" && todos.length > 0) {
      heading.textContent = "没有进行中的任务";
      paragraph.textContent = "不错，当前任务都已经完成了。";
    } else if (currentFilter === "completed") {
      heading.textContent = "还没有已完成任务";
      paragraph.textContent = "完成一个任务后，它会出现在这里。";
    } else {
      heading.textContent = "还没有任务";
      paragraph.textContent = "从添加第一件待办开始吧。";
    }
  }
}

function addTodo(text) {
  todos.unshift(createTodo(text));
  saveTodos();
  render();
}

function toggleTodo(id) {
  todos = todos.map((todo) =>
    todo.id === id ? { ...todo, completed: !todo.completed } : todo
  );
  saveTodos();
  render();
}

function deleteTodo(id) {
  todos = todos.filter((todo) => todo.id !== id);
  saveTodos();
  render();
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();

  if (!text) return;

  addTodo(text);
  input.value = "";
  input.focus();
});

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    filterButtons.forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
});

clearCompleted.addEventListener("click", () => {
  todos = todos.filter((todo) => !todo.completed);
  saveTodos();
  render();
});

render();
