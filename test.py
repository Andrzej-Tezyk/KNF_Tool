# print all numbers to n, which are dividable on 0, itself or 1

def prime_numbers(n):

    result = []

    for number in range(n):
        count = 0
        divider = n
        while divider > 0:
            #print(divider)
            if number % divider == 0:
                count += 1
            divider -= 1
        #print(count)
        if count == 2 and number != 2:
            result.append(number)
    
    return result

print(prime_numbers(1000))