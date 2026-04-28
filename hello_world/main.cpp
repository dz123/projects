#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <cmath>
#include <limits>

float parseValue(const std::string& s) {
    if (s == "inf")  return  std::numeric_limits<float>::infinity();
    if (s == "-inf") return -std::numeric_limits<float>::infinity();
    if (s == "nan")  return  std::numeric_limits<float>::quiet_NaN();
    return std::stof(s);
}

// Compute the average of the current window, handling non-finite values.
// Rules:
//   - any NaN in window          -> NaN
//   - both +inf and -inf present -> NaN  (they cancel)
//   - only +inf present          -> +inf
//   - only -inf present          -> -inf
//   - all finite                 -> sum / k
float windowAverage(float finiteSum, int posInfCount, int negInfCount, int nanCount, int k) {
    bool hasNan        = nanCount > 0;
    bool hasConflict   = posInfCount > 0 && negInfCount > 0;
    if (hasNan || hasConflict)  return std::numeric_limits<float>::quiet_NaN();
    if (posInfCount > 0)        return  std::numeric_limits<float>::infinity();
    if (negInfCount > 0)        return -std::numeric_limits<float>::infinity();
    return finiteSum / k;
}

std::vector<float> movingAverage(const std::vector<float>& input_values, int k) {
    int n = (int)input_values.size();
    std::vector<float> output;
    if (n < k) return output;

    // Running totals for the current window
    float finiteSum  = 0.0f;
    int posInfCount  = 0;
    int negInfCount  = 0;
    int nanCount     = 0;

    // Fill the first window
    for (int i = 0; i < k; i++) {
        float v = input_values[i];
        if (std::isnan(v))         nanCount++;
        else if (std::isinf(v))    v > 0 ? posInfCount++ : negInfCount++;
        else                       finiteSum += v;
    }
    output.push_back(windowAverage(finiteSum, posInfCount, negInfCount, nanCount, k));

    // Slide the window across the rest of the array
    for (int i = k; i < n; i++) {
        // Add the new value entering the window
        float newVal = input_values[i];
        if (std::isnan(newVal))         nanCount++;
        else if (std::isinf(newVal))    newVal > 0 ? posInfCount++ : negInfCount++;
        else                            finiteSum += newVal;

        // Remove the old value leaving the window
        float oldVal = input_values[i - k];
        if (std::isnan(oldVal))         nanCount--;
        else if (std::isinf(oldVal))    oldVal > 0 ? posInfCount-- : negInfCount--;
        else                            finiteSum -= oldVal;

        output.push_back(windowAverage(finiteSum, posInfCount, negInfCount, nanCount, k));
    }

    return output;
}

void printResult(const std::vector<float>& output) {
    std::cout << "[";
    for (int i = 0; i < (int)output.size(); i++) {
        if (i > 0) std::cout << ",";
        float v = output[i];
        if      (std::isnan(v))        std::cout << "nan";
        else if (std::isinf(v) && v>0) std::cout << "inf";
        else if (std::isinf(v) && v<0) std::cout << "-inf";
        else                           std::cout << v;
    }
    std::cout << "]\n";
}

int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;

        // Parse the line: first token is k, rest are the input values
        std::istringstream iss(line);
        std::string token;
        std::vector<std::string> tokens;
        while (iss >> token) tokens.push_back(token);
        if (tokens.empty()) continue;

        int k = std::stoi(tokens[0]);
        std::vector<float> input_values;
        for (int i = 1; i < (int)tokens.size(); i++)
            input_values.push_back(parseValue(tokens[i]));

        printResult(movingAverage(input_values, k));
    }
    return 0;
}
