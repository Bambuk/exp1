# AI Session Guide - Quick Reference

## 🚀 **Start of Session Checklist**

1. **Read this file** - follow guidelines below
2. **Ask clarifying questions** - requirements, constraints, approach
3. **Suggest TDD** - "Should we start with tests first?"
4. **Create plan** - break into small, testable steps
5. **Begin with tests** - integration tests preferred over mocks

## ⚠️ **When User Deviates - Remind Them**

### **Skip Tests?**
> "Following TDD best practices, should we create tests first to ensure our implementation works correctly?"

### **Skip Planning?**
> "Before we start coding, would you like me to create a detailed plan? This helps ensure we don't miss important edge cases."

### **Big Commit?**
> "Should we commit this incrementally? This makes it easier to track changes and rollback if needed."

### **Skip Cleanup?**
> "Should we clean up temporary files and update documentation before finalizing?"

## 🚫 **NEVER Do Without Asking**

### **If you want to fix failing tests:**
> "I see some tests are failing. Should I create a plan to fix these tests?"

### **If you want to refactor/optimize:**
> "Would you like me to refactor this code for better readability/performance?"

### **If you want to add features:**
> "Should I add [feature] to improve this functionality?"

### **If you want to do anything not explicitly requested:**
> "I notice [observation]. Would you like me to [suggested action]?"

**Rule: Only do what the user explicitly asked for. Everything else - ask first!**

## 🎯 **Development Process**

```
1. Plan → 2. Tests → 3. Code → 4. Test → 5. Refactor → 6. Cleanup → 7. Commit
```

## 🧪 **Testing Priority**
1. **Integration tests** (real DB) - BEST
2. **Unit tests** (minimal mocking) - GOOD
3. **Mock tests** (only when necessary) - AVOID

## 📁 **File Management**
- Temporary files → `temp/` directory
- Clean up after each phase
- Don't commit temporary files

## ✅ **Success Criteria**
- All tests pass
- Clean, documented code
- No temp files left
- Meaningful commits
- User understands implementation

---
**Remember: Suggest best practices when user deviates, but respect their final decision.**
