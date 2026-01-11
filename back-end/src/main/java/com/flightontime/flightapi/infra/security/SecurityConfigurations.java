package com.flightontime.flightapi.infra.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfigurations {

    private static final Logger log = LoggerFactory.getLogger(SecurityConfigurations.class);

    @Autowired
    private SecurityFilter securityFilter;

    public static final String [] ENDPOINTS_POST_NO_AUTH = {"/auth/**", "/predict"};
    public static final String [] ENDPOINTS_GET_NO_AUTH = {"/", "/check/**", "/h2-console/**", "/generate_204", "/actuator/**", "/gerar-password", "/airports", "/airlines"};
    public static final String [] ENDPOINTS_SWAGGER = {"/v3/api-docs/**", "/swagger-ui.html", "/swagger-ui/**"};
    public static final String [] ENDPOINTS_ADMIN = {"/admin", "/users/**"};

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        log.info("SecurityConfigurations.SecurityFilterChain");
        return http.csrf(AbstractHttpConfigurer::disable)
                .cors(cors -> {})
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(req -> {
                    req.requestMatchers(HttpMethod.POST, ENDPOINTS_POST_NO_AUTH).permitAll();
                    req.requestMatchers(HttpMethod.GET, ENDPOINTS_GET_NO_AUTH).permitAll();
                    req.requestMatchers(ENDPOINTS_SWAGGER).permitAll();
                    req.requestMatchers(ENDPOINTS_ADMIN).hasRole("ADMIN");
                    req.anyRequest().authenticated();
                })
                .addFilterBefore(securityFilter, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration configuration) throws Exception {
        log.info("SecurityConfigurations.AuthenticationManager");
        return configuration.getAuthenticationManager();
    }

    @Bean
    public PasswordEncoder passwordEncoder(){
        return new BCryptPasswordEncoder();
    }

}
