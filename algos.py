size = 5

list = [[i+1 for i in range(size)]]
for s in range(1, size+1):
    list.append(a+b for a, b in zip(list[0]*s, list[0]))

print(list)